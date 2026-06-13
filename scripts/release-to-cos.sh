#!/bin/bash
# Download Codex Switch release from GitHub and upload to Tencent Cloud COS.
#
# This is a convenience wrapper around:
#   ./scripts/download-latest-release.sh  (download from GitHub)
#   ./scripts/upload-to-cos.sh            (upload to COS)
#
# Usage:
#   ./scripts/release-to-cos.sh -v 1.8.0         # specific version
#   ./scripts/release-to-cos.sh --latest          # auto-detect latest from GitHub
#   ./scripts/release-to-cos.sh -v 1.8.0 --dry-run  # preview only
#
# Requires GITHUB_TOKEN in .env and COS credentials in .env.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOWNLOAD_SCRIPT="${SCRIPT_DIR}/download-latest-release.sh"
UPLOAD_SCRIPT="${SCRIPT_DIR}/upload-to-cos.sh"

# ── Parse args ──────────────────────────────────────────

VERSION=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -v|--version) VERSION="$2"; shift 2 ;;
    --latest)     VERSION=""; shift ;;
    --dry-run)    DRY_RUN=true; shift ;;
    -h|--help)
      echo "Usage: $0 [-v VERSION | --latest] [--dry-run]"
      echo ""
      echo "Download a Codex Switch release from GitHub and upload to COS Guangzhou."
      echo ""
      echo "Options:"
      echo "  -v, --version VER   Specific version (e.g. 1.8.0)"
      echo "  --latest            Auto-detect latest version from GitHub"
      echo "  --dry-run           Preview only, no actual download or upload"
      echo ""
      echo "Example:"
      echo "  $0 -v 1.8.0                  # download + upload v1.8.0"
      echo "  $0 --latest --dry-run        # preview latest release"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Build download args ─────────────────────────────────

DOWNLOAD_ARGS=()
if [ -n "$VERSION" ]; then
  DOWNLOAD_ARGS+=(-v "$VERSION")
fi
if [ "$DRY_RUN" = true ]; then
  DOWNLOAD_ARGS+=(--dry-run)
  UPLOAD_DRY="--dry-run"
else
  UPLOAD_DRY=""
fi

# ── Step 1: Download from GitHub ────────────────────────

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Step 1/2: Download from GitHub                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

bash "$DOWNLOAD_SCRIPT" "${DOWNLOAD_ARGS[@]}"

# ── Step 2: Upload to COS ───────────────────────────────

VERSION_ARG="${VERSION:-latest}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Step 2/2: Upload to COS Guangzhou                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

bash "$UPLOAD_SCRIPT" --codex-switch "$VERSION_ARG" $UPLOAD_DRY

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Done!                                              ║"
echo "╚══════════════════════════════════════════════════════╝"
