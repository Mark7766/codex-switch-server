#!/bin/bash
# Download the latest Codex Switch release assets from GitHub.
# Saves files to data/codex-switch/{version}/ with original filenames (COS-ready).
# Also creates simplified-name copies for local server cache.
#
# Usage:
#   ./scripts/download-latest-release.sh              # auto-detect latest version
#   ./scripts/download-latest-release.sh -v 1.5.4     # specific version
#   ./scripts/download-latest-release.sh --dry-run    # preview only, no download
#   ./scripts/download-latest-release.sh --local-cache # also create simplified-name copies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── Parse args ──────────────────────────────────────────

VERSION=""
DRY_RUN=false
LOCAL_CACHE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -v|--version) VERSION="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --local-cache) LOCAL_CACHE=true; shift ;;
    -h|--help)
      echo "Usage: $0 [-v VERSION] [--dry-run] [--local-cache]"
      echo ""
      echo "Options:"
      echo "  -v, --version VERSION  Download a specific version (e.g. v1.5.4)"
      echo "                         If omitted, auto-detects the latest release."
      echo "  --dry-run              Show what would be downloaded without downloading."
      echo "  --local-cache          Also create simplified-name copies for local server cache"
      echo "                         (e.g. macos-arm64.dmg alongside Codex-Switch-1.5.4-mac-arm64.dmg)"
      echo "  -h, --help             Show this help message."
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Load env ────────────────────────────────────────────

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a; source "$PROJECT_DIR/.env"; set +a
fi

GITHUB_REPO="Mark7766/codex-switch"
GITHUB_API="https://api.github.com/repos/${GITHUB_REPO}/releases"
DATA_DIR="$PROJECT_DIR/data/codex-switch"

# ── Helpers ─────────────────────────────────────────────

log_info()  { echo "  ℹ️  $*"; }
log_ok()    { echo "  ✅ $*"; }
log_warn()  { echo "  ⚠️  $*"; }
log_error() { echo "  ❌ $*"; }

# ── Common headers for GitHub API ──────────────────────────

API_HEADERS=(-H "Accept: application/vnd.github+json")
if [ -n "${GITHUB_TOKEN:-}" ]; then
  API_HEADERS+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

# ── Fetch latest version ────────────────────────────────

if [ -z "$VERSION" ]; then
  echo "=== Detecting latest Codex Switch release ==="
  echo "Repo: ${GITHUB_REPO}"
  echo ""

  # Fetch latest release tag from GitHub API
  RELEASES_JSON=$(curl -fsSL "${API_HEADERS[@]}" "${GITHUB_API}?per_page=1" 2>&1) || {
    log_error "Failed to fetch GitHub releases. Check GITHUB_TOKEN in .env"
    exit 1
  }

  VERSION=$(echo "$RELEASES_JSON" | uv run python3 -c "
import json, sys
data = json.load(sys.stdin)
if not data:
    sys.exit(1)
latest = data[0] if isinstance(data, list) else data
print(latest['tag_name'])
" 2>&1) || {
    log_error "Failed to parse release tag from GitHub API response."
    echo "$RELEASES_JSON" | head -20
    exit 1
  }

  log_ok "Latest version: ${VERSION}"
  echo ""
fi

# ── Fetch assets for the version ────────────────────────

# Normalize tag: GitHub uses v1.8.0 format, but user may pass 1.8.0
TAG="${VERSION}"
[[ "$TAG" != v* ]] && TAG="v${TAG}"

echo "=== Fetching asset list for ${VERSION} (tag: ${TAG}) ==="
echo ""

# Get the specific release by tag
RELEASE_JSON=$(curl -fsSL "${API_HEADERS[@]}" "${GITHUB_API}/tags/${TAG}" 2>&1) || {
  log_error "Failed to fetch release for tag ${VERSION}. Check that the tag exists."
  exit 1
}

# Parse assets into: original_filename|platform|arch|ext|size|download_url
ASSETS=$(echo "$RELEASE_JSON" | uv run python3 -c "
import json, sys

data = json.load(sys.stdin)
assets = data.get('assets', [])

def detect_platform(name):
    n = name.lower()
    # Skip non-installer files
    if '.blockmap' in n or n.endswith('.yml') or n.endswith('.yaml') or n.endswith('.zip'):
        return (None, None, None)

    plat = None
    arch = 'x64'
    ftype = None

    if '.dmg' in n:
        plat, ftype = 'macos', 'dmg'
    elif '.exe' in n:
        plat, ftype = 'windows', 'exe'
    elif '.appimage' in n:
        plat, ftype = 'linux', 'appimage'

    if not plat:
        return (None, None, None)

    if 'arm64' in n or 'aarch64' in n:
        arch = 'arm64'
    elif plat == 'windows' and 'x64' not in n and 'x86' not in n and 'amd64' not in n:
        # Windows .exe must have explicit arch
        return (None, None, None)

    return (plat, arch, ftype)

for a in assets:
    name = a['name']
    plat, arch, ftype = detect_platform(name)
    if plat:
        print(f\"{name}|{plat}|{arch}|{ftype}|{a['size']}|{a['browser_download_url']}\")
")

if [ -z "$ASSETS" ]; then
  log_error "No installable assets found for ${VERSION}."
  echo "Raw assets:"
  echo "$RELEASE_JSON" | uv run python3 -c "
import json, sys
for a in json.load(sys.stdin).get('assets', []):
    print(f\"  {a['name']}  ({a['size']} bytes)\")
"
  exit 1
fi

# ── Display what will be downloaded ──────────────────────

echo "Assets to download:"
echo ""
printf "  %-50s %8s  %s\n" "FILENAME" "SIZE" "PLATFORM"
printf "  %-50s %8s  %s\n" "──────" "────" "────────"
total_size=0
while IFS='|' read -r filename plat arch ftype size url; do
  size_mb=$(echo "scale=1; $size / 1048576" | bc 2>/dev/null || echo "$size")
  printf "  %-50s %6s MB  %s-%s\n" "$filename" "$size_mb" "$plat" "$arch"
  total_size=$((total_size + size))
done <<< "$ASSETS"
echo ""
total_mb=$(echo "scale=1; $total_size / 1048576" | bc 2>/dev/null || echo "$total_size")
echo "Total: $(echo "$ASSETS" | wc -l | tr -d ' ') files, ~${total_mb} MB"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "Dry run — no files downloaded. Remove --dry-run to download."
  exit 0
fi

# ── Download ─────────────────────────────────────────────

DEST_DIR="${DATA_DIR}/${VERSION#v}"
mkdir -p "$DEST_DIR"

echo "=== Downloading to ${DEST_DIR} ==="
echo ""

downloaded=0
while IFS='|' read -r filename plat arch ftype size url; do
  dest="${DEST_DIR}/${filename}"
  simple_name="${DEST_DIR}/${plat}-${arch}.${ftype}"

  echo "[${filename}]"
  log_info "Platform: ${plat}-${arch}  Size: $(echo "scale=1; $size / 1048576" | bc) MB"
  log_info "URL: ${url}"

  if [ -f "$dest" ]; then
    local_size=$(wc -c < "$dest" 2>/dev/null | tr -d ' ')
    if [ "$local_size" -eq "$size" ]; then
      log_ok "Already downloaded (size match). Skipping."
    else
      log_warn "Local file size mismatch (local: $local_size, remote: $size). Re-downloading."
      curl -fSL --progress-bar -o "$dest" "$url"
      log_ok "Downloaded: ${dest}"
    fi
  else
    curl -fSL --progress-bar -o "$dest" "$url"
    downloaded=$((downloaded + 1))
    log_ok "Downloaded: ${dest}"
  fi

  # Create simplified-name copy for local server cache
  if [ "$LOCAL_CACHE" = true ] || [ ! -f "$simple_name" ]; then
    cp "$dest" "$simple_name"
    [ "$LOCAL_CACHE" = true ] && log_info "Local cache: ${simple_name}"
  fi

  echo ""
done <<< "$ASSETS"

# ── Summary ──────────────────────────────────────────────

echo "=== Done: ${VERSION} ==="
echo "  Downloaded:  ${downloaded} new file(s)"
echo "  Destination: ${DEST_DIR}"
ls -lh "$DEST_DIR" | tail -n +2
echo ""

if [ "$LOCAL_CACHE" = true ]; then
  echo "  Local cache copies created with simplified names (ready for uvicorn)."
elif [ ! -f "${DEST_DIR}/macos-arm64.dmg" ]; then
  echo ""
  echo "💡 Tip: Run with --local-cache to also create simplified-name copies for local server cache."
  echo "   The local server needs files named like: macos-arm64.dmg, windows-x64.exe, etc."
fi
