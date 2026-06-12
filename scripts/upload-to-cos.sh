#!/bin/bash
# Upload installation packages to Tencent Cloud COS (Guangzhou).
#
# Supports three categories:
#   1. Codex Switch releases: from data/codex-switch/{version}/
#   2. Desktop app packages:   from data/packages/{name}/X/  (via registry.json)
#   3. Static files:           from data/files/
#
# Usage:
#   ./scripts/upload-to-cos.sh                          # upload everything (default)
#   ./scripts/upload-to-cos.sh --all                    # upload everything
#   ./scripts/upload-to-cos.sh --codex-switch 1.5.4     # only Codex Switch v1.5.4
#   ./scripts/upload-to-cos.sh --codex-switch latest    # auto-detect latest from GitHub
#   ./scripts/upload-to-cos.sh --packages               # only desktop app packages
#   ./scripts/upload-to-cos.sh --files                  # only static files (2.1.138.zip etc.)
#   ./scripts/upload-to-cos.sh --dry-run                # preview without uploading

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Parse args ──────────────────────────────────────────

MODE="all"
VERSION=""
DRY_RUN=false
SKIP_EXISTING=true
GH_REPO="Mark7766/codex-switch"
GH_API="https://api.github.com/repos/${GH_REPO}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --all)            MODE="all"; shift ;;
    --codex-switch)   MODE="codex-switch"; VERSION="${2:-latest}"; shift 2 ;;
    --packages)       MODE="packages"; shift ;;
    --files)          MODE="files"; shift ;;
    --dry-run)        DRY_RUN=true; shift ;;
    --force)          SKIP_EXISTING=false; shift ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --all                  Upload everything (default): Codex Switch + packages + files"
      echo "  --codex-switch VER     Upload Codex Switch release files. VER can be 'latest'"
      echo "                         or a specific version like '1.5.4'"
      echo "  --packages             Upload desktop app packages (from registry.json)"
      echo "  --files                Upload static files (from data/files/)"
      echo "  --dry-run              Preview what would be uploaded without uploading"
      echo "  --force                Upload even if COS object already exists"
      echo "  -h, --help             Show this help message"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Load env ────────────────────────────────────────────

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a; source "$PROJECT_DIR/.env"; set +a
fi

: "${COS_SECRET_ID:?COS_SECRET_ID not set in .env}"
: "${COS_SECRET_KEY:?COS_SECRET_KEY not set in .env}"
: "${COS_BUCKET:?COS_BUCKET not set in .env}"
: "${COS_REGION:=ap-guangzhou}"

COS_BASE="https://${COS_BUCKET}.cos.${COS_REGION}.myqcloud.com"
DATA_DIR="$PROJECT_DIR/data"

# ── Helpers ─────────────────────────────────────────────

log_info()  { echo "  ℹ️  $*"; }
log_ok()    { echo "  ✅ $*"; }
log_warn()  { echo "  ⚠️  $*"; }
log_error() { echo "  ❌ $*"; }

# Upload a single file to COS using Python SDK.
# Args: local_path cos_key content_disposition
_cos_upload() {
  local local_path="$1"
  local cos_key="$2"
  local disposition="$3"

  if [ ! -f "$local_path" ]; then
    log_error "File not found: ${local_path}"
    return 1
  fi

  local size=$(ls -lh "$local_path" | awk '{print $5}')
  echo "  File: $(basename "$local_path") (${size})"
  echo "  Key:  ${cos_key}"

  if [ "$DRY_RUN" = true ]; then
    echo "  ⏭️  Dry run — skipping upload."
    echo ""
    return 0
  fi

  # Check if already exists on COS
  if [ "$SKIP_EXISTING" = true ]; then
    local exists=$(uv run python3 -c "
from qcloud_cos import CosConfig, CosS3Client
config = CosConfig(Region='${COS_REGION}', SecretId='${COS_SECRET_ID}', SecretKey='${COS_SECRET_KEY}')
client = CosS3Client(config)
try:
    client.head_object(Bucket='${COS_BUCKET}', Key='${cos_key}')
    print('yes')
except:
    print('no')
" 2>/dev/null)
    if [ "$exists" = "yes" ]; then
      echo "  ⏭️  Already on COS. Use --force to re-upload."
      echo ""
      return 0
    fi
  fi

  # Upload
  uv run python3 -c "
import sys
from urllib.parse import quote
from qcloud_cos import CosConfig, CosS3Client
config = CosConfig(Region='${COS_REGION}', SecretId='${COS_SECRET_ID}', SecretKey='${COS_SECRET_KEY}')
client = CosS3Client(config)
client.put_object_from_local_file(
    Bucket='${COS_BUCKET}',
    LocalFilePath='${local_path}',
    Key='${cos_key}',
    ContentDisposition='${disposition}',
)
" 2>&1 || {
    log_error "Upload failed: ${cos_key}"
    return 1
  }

  log_ok "Uploaded → ${COS_BASE}/${cos_key}"
  echo ""
}

# URL-encode a string for Content-Disposition filename
_url_encode() {
  uv run python3 -c "from urllib.parse import quote; print(quote('$1'))"
}

# ── 1. Codex Switch releases ────────────────────────────

# Resolve the mapping from simplified filenames → original GitHub filenames
# by querying the GitHub release API.
# Output format: simplename|original_name|download_url
#   e.g.: macos-arm64.dmg|Codex-Switch-1.5.4-mac-arm64.dmg|https://...
_resolve_original_names() {
  local ver="$1"
  local api_headers=(-H "Accept: application/vnd.github+json")
  [ -n "${GITHUB_TOKEN:-}" ] && api_headers+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")

  curl -fsSL "${api_headers[@]}" "${GH_API}/releases/tags/v${ver}" | uv run python3 -c "
import json, sys

data = json.load(sys.stdin)

def detect_platform(name):
    n = name.lower()
    if '.blockmap' in n or n.endswith('.yml') or n.endswith('.yaml') or n.endswith('.zip'):
        return None, None, None
    plat, arch, ftype = None, 'x64', None
    if '.dmg' in n:
        plat, ftype = 'macos', 'dmg'
    elif '.exe' in n:
        plat, ftype = 'windows', 'exe'
    elif '.appimage' in n:
        plat, ftype = 'linux', 'appimage'
    if not plat:
        return None, None, None
    if 'arm64' in n or 'aarch64' in n:
        arch = 'arm64'
    elif plat == 'windows' and 'x64' not in n and 'x86' not in n:
        return None, None, None
    return plat, arch, ftype

for a in data.get('assets', []):
    name = a['name']
    plat, arch, ftype = detect_platform(name)
    if plat:
        simple = f'{plat}-{arch}.{ftype}'
        print(f'{simple}|{name}|{a[\"browser_download_url\"]}')
"
}

_upload_codex_switch() {
  local ver="$1"

  # Resolve 'latest' to actual version tag
  if [ "$ver" = "latest" ]; then
    echo "=== Resolving latest Codex Switch version from GitHub ==="
    echo ""

    local api_headers=(-H "Accept: application/vnd.github+json")
    [ -n "${GITHUB_TOKEN:-}" ] && api_headers+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")

    local latest_tag
    latest_tag=$(curl -fsSL "${api_headers[@]}" "${GH_API}/releases?per_page=1" | \
      uv run python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['tag_name'] if d else '')" 2>/dev/null)

    if [ -z "$latest_tag" ]; then
      log_error "Failed to fetch latest release tag from GitHub."
      log_error "Specify a version explicitly: --codex-switch v1.5.4"
      return 1
    fi
    ver="${latest_tag#v}"  # strip leading 'v'
    log_ok "Latest version: v${ver}"
    echo ""
  else
    ver="${ver#v}"  # strip leading 'v' if present
  fi

  local src_dir="${DATA_DIR}/codex-switch/${ver}"
  if [ ! -d "$src_dir" ]; then
    log_error "Directory not found: ${src_dir}"
    log_error ""
    log_error "Run this first to download the release files:"
    log_error "  ./scripts/download-latest-release.sh -v ${ver}"
    return 1
  fi

  echo "=== Uploading Codex Switch v${ver} to COS ==="
  echo "Source: ${src_dir}"
  echo ""

  # Get the mapping from simplified names → original GitHub filenames
  local name_map
  name_map=$(_resolve_original_names "$ver" 2>/dev/null)

  if [ -z "$name_map" ]; then
    log_warn "Could not resolve original filenames from GitHub API."
    log_warn "Falling back to local files as-is."
    name_map=""
  fi

  # Helper: look up original name from the name_map (simplified_name → original_name)
  _lookup_orig_name() {
    local simple="$1"
    local found=""
    if [ -n "$name_map" ]; then
      while IFS='|' read -r s o u; do
        [ "$s" = "$simple" ] && found="$o" && break
      done <<< "$name_map"
    fi
    echo "$found"
  }

  local file_count=0
  local uploaded=0

  # First pass: upload files that have original GitHub names (preferred)
  for f in "$src_dir"/Codex-Switch-* "$src_dir"/Codex-Switch-Setup-*; do
    [ -f "$f" ] || continue
    local fname
    fname=$(basename "$f")
    local cos_key="codex-switch/${ver}/${fname}"
    local encoded_name
    encoded_name=$(_url_encode "$fname")
    local disposition="attachment; filename*=UTF-8''${encoded_name}"

    echo "[${fname}]"
    _cos_upload "$f" "$cos_key" "$disposition" && uploaded=$((uploaded + 1))
    file_count=$((file_count + 1))
  done

  # Second pass: upload simplified-name files, using the original name as COS key
  for f in "$src_dir"/*; do
    [ -f "$f" ] || continue
    local fname
    fname=$(basename "$f")

    # Skip non-matching files and already-processed original-name files
    if [[ ! "$fname" =~ ^[a-z]+-[a-z0-9]+\.(dmg|exe|appimage)$ ]]; then
      continue
    fi

    # Look up the original GitHub filename from the name map
    local orig_name
    orig_name=$(_lookup_orig_name "$fname")

    if [ -z "$orig_name" ]; then
      # No mapping found — try to infer from the version and platform
      # macOS: Codex-Switch-{ver}-mac-{arch}.dmg
      # Windows: Codex-Switch-Setup-{ver}-win-{arch}.exe
      local plat="${fname%%-*}"
      local rest="${fname#*-}"
      local arch="${rest%.*}"
      arch="${arch#*-}"
      if [ "$plat" = "macos" ]; then
        orig_name="Codex-Switch-${ver}-mac-${arch}.dmg"
      elif [ "$plat" = "windows" ]; then
        orig_name="Codex-Switch-Setup-${ver}-win-${arch}.exe"
      else
        orig_name="$fname"
      fi
      log_warn "No original name mapping for ${fname}, using inferred: ${orig_name}"
    fi

    local cos_key="codex-switch/${ver}/${orig_name}"
    local encoded_name
    encoded_name=$(_url_encode "$orig_name")
    local disposition="attachment; filename*=UTF-8''${encoded_name}"

    echo "[${fname}]"
    _cos_upload "$f" "$cos_key" "$disposition" && uploaded=$((uploaded + 1))
    file_count=$((file_count + 1))
  done

  echo "=== Codex Switch: ${file_count} file(s) found, ${uploaded} uploaded ==="
  echo ""
}

# ── 2. Desktop app packages ─────────────────────────────

_upload_packages() {
  local registry="${DATA_DIR}/packages/registry.json"

  if [ ! -f "$registry" ]; then
    log_warn "registry.json not found at ${registry}. Skipping packages."
    return 0
  fi

  echo "=== Uploading desktop app packages to COS ==="
  echo ""

  # Parse registry and upload each platform's file
  local pkg_count=0
  local entries
  entries=$(uv run python3 -c "
import json
with open('${registry}') as f:
    reg = json.load(f)
for pkg in reg.get('packages', []):
    name = pkg['name']
    for plat in pkg.get('platforms', []):
        pp = plat['platform']
        arch = plat['arch']
        ftype = plat.get('file_type', 'bin')
        local_path = plat.get('path', '')
        orig_name = plat.get('original_filename', '')
        # path looks like: packages/codex-desktop/X/windows-x64.exe
        # Local file: data/packages/codex-desktop/X/windows-x64.exe
        print(f\"{name}|{pp}|{arch}|{ftype}|{local_path}|{orig_name}\")
")

  while IFS='|' read -r name plat arch ftype path orig_name; do
    [ -z "$name" ] && continue

    local local_file="${DATA_DIR}/${path}"
    local cos_key="packages/${name}/latest/${plat}-${arch}.${ftype}"

    # Content-Disposition: use original filename if available
    local disposition=""
    if [ -n "$orig_name" ]; then
      local encoded
      encoded=$(_url_encode "$orig_name")
      disposition="attachment; filename*=UTF-8''${encoded}"
    else
      local fallback_name="${name}-${plat}-${arch}.${ftype}"
      local encoded
      encoded=$(_url_encode "$fallback_name")
      disposition="attachment; filename*=UTF-8''${encoded}"
    fi

    echo "[${name}] ${plat}-${arch}"
    _cos_upload "$local_file" "$cos_key" "$disposition"
    pkg_count=$((pkg_count + 1))
  done <<< "$entries"

  echo "=== Packages: ${pkg_count} file(s) processed ==="
  echo ""
}

# ── 3. Static files ─────────────────────────────────────

_upload_files() {
  local src_dir="${DATA_DIR}/files"

  if [ ! -d "$src_dir" ] || [ -z "$(ls -A "$src_dir" 2>/dev/null)" ]; then
    log_info "No static files in ${src_dir}. Skipping."
    return 0
  fi

  echo "=== Uploading static files to COS ==="
  echo ""

  local file_count=0
  for f in "$src_dir"/*; do
    [ -f "$f" ] || continue
    local fname
    fname=$(basename "$f")
    local cos_key="files/${fname}"
    local encoded
    encoded=$(_url_encode "$fname")
    local disposition="attachment; filename*=UTF-8''${encoded}"

    _cos_upload "$f" "$cos_key" "$disposition"
    file_count=$((file_count + 1))
  done

  echo "=== Static files: ${file_count} file(s) processed ==="
  echo ""
}

# ── Main dispatch ───────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  COS Upload — ${COS_BUCKET}                  ║"
echo "║  Region: ${COS_REGION}                               ║"
if [ "$DRY_RUN" = true ]; then
  echo "║  MODE: DRY RUN (no actual upload)           ║"
fi
echo "╚══════════════════════════════════════════════╝"
echo ""

case "$MODE" in
  all)
    # Codex Switch: auto-detect latest version
    _upload_codex_switch "latest" || true
    _upload_packages
    _upload_files
    ;;
  codex-switch)
    _upload_codex_switch "$VERSION"
    ;;
  packages)
    _upload_packages
    ;;
  files)
    _upload_files
    ;;
esac

echo "╔══════════════════════════════════════════════╗"
if [ "$DRY_RUN" = true ]; then
  echo "║  Dry run complete.                           ║"
else
  echo "║  All uploads complete.                       ║"
fi
echo "╚══════════════════════════════════════════════╝"
echo ""

if [ "$DRY_RUN" = false ]; then
  echo "💡 Tip: Run the app and test COS download links:"
  echo "   curl -I https://www.codexswtich.cloud/api/v1/update/download/1.5.4/macos-arm64"
  echo ""
fi
