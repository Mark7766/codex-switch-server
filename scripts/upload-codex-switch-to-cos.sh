#!/bin/bash
# Upload Codex Switch release files to Tencent Cloud COS.
# Run after each new version deployment.
# Usage: ./scripts/upload-codex-switch-to-cos.sh v1.4.0

set -euo pipefail

VERSION="${1:?Usage: $0 <version> (e.g. v1.4.0)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load COS credentials from .env
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a; source "$PROJECT_DIR/.env"; set +a
fi

: "${COS_SECRET_ID:?COS_SECRET_ID not set}"
: "${COS_SECRET_KEY:?COS_SECRET_KEY not set}"
: "${COS_BUCKET:?COS_BUCKET not set}"
: "${COS_REGION:=ap-guangzhou}"

COS_BASE="https://${COS_BUCKET}.cos.${COS_REGION}.myqcloud.com"
GH_RELEASES="https://github.com/Mark7766/codex-switch/releases/download"

# 4 platform files
declare -A FILES=(
  ["Codex-Switch-${VERSION}-mac-arm64.dmg"]="${GH_RELEASES}/${VERSION}/Codex-Switch-${VERSION}-mac-arm64.dmg"
  ["Codex-Switch-${VERSION}-mac-x64.dmg"]="${GH_RELEASES}/${VERSION}/Codex-Switch-${VERSION}-mac-x64.dmg"
  ["Codex-Switch-Setup-${VERSION}-win-arm64.exe"]="${GH_RELEASES}/${VERSION}/Codex-Switch-Setup-${VERSION}-win-arm64.exe"
  ["Codex-Switch-Setup-${VERSION}-win-x64.exe"]="${GH_RELEASES}/${VERSION}/Codex-Switch-Setup-${VERSION}-win-x64.exe"
)

echo "=== Uploading Codex Switch ${VERSION} to COS ==="
echo "Bucket: ${COS_BUCKET}"
echo "Region: ${COS_REGION}"
echo ""

for filename in "${!FILES[@]}"; do
  url="${FILES[$filename]}"
  cos_key="codex-switch/${VERSION}/${filename}"

  echo "[${filename}]"
  echo "  Download: ${url}"
  echo "  COS key:  ${cos_key}"

  # Download from GitHub to temp
  tmpfile="/tmp/${filename}"
  curl -fsSL -o "$tmpfile" "$url"
  echo "  Downloaded: $(ls -lh "$tmpfile" | awk '{print $5}')"

  # Upload to COS using Python SDK
  uv run python3 -c "
import os
from urllib.parse import quote
from qcloud_cos import CosConfig, CosS3Client
config = CosConfig(Region='${COS_REGION}', SecretId='${COS_SECRET_ID}', SecretKey='${COS_SECRET_KEY}')
client = CosS3Client(config)
disposition = f\"attachment; filename*=UTF-8''{quote('${filename}')}\"
client.put_object_from_local_file(
    Bucket='${COS_BUCKET}',
    LocalFilePath='${tmpfile}',
    Key='${cos_key}',
    ContentDisposition=disposition,
)
print(f'  Upload OK → ${COS_BASE}/${cos_key}')
"
  rm -f "$tmpfile"
  echo ""
done

echo "=== Done: ${#FILES[@]} files uploaded ==="
