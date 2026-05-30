#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "usage: $0 <platform> <url> <artifact-output> <metadata-output>" >&2
  exit 64
fi

platform="$1"
url="$2"
artifact_output="$3"
metadata_output="$4"
macos_url="https://persistent.oaistatic.com/codex-app-prod/Codex.dmg"

tmpdir="$(mktemp -d)"
headers_file="$tmpdir/headers.txt"
metrics_file="$tmpdir/metrics.txt"
python_bin="${PYTHON:-python3}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin="python"
fi

cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

mkdir -p "$(dirname "$artifact_output")" "$(dirname "$metadata_output")"

case "${platform}:${url}" in
  "macos:${macos_url}") ;;
  *)
    echo "Refusing to download unapproved source URL for platform '${platform}': ${url}" >&2
    exit 65
    ;;
esac

curl \
  --proto '=https' \
  --tlsv1.2 \
  --fail \
  --show-error \
  --silent \
  --dump-header "$headers_file" \
  --output "$artifact_output" \
  --write-out 'effective_url=%{url_effective}\nhttp_code=%{http_code}\ncontent_type=%{content_type}\nsize_download=%{size_download}\n' \
  "$url" > "$metrics_file"

"$python_bin" - "$platform" "$url" "$headers_file" "$metrics_file" "$metadata_output" <<'PY'
import json
import re
import sys
from pathlib import Path

platform, url, headers_path, metrics_path, output_path = sys.argv[1:]

metrics = {}
for line in Path(metrics_path).read_text(encoding="utf-8").splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        metrics[key] = value

headers_text = Path(headers_path).read_text(encoding="iso-8859-1")
blocks = [block for block in re.split(r"\r?\n\r?\n", headers_text) if block.strip()]
final_block = blocks[-1] if blocks else ""
lines = final_block.splitlines()
status_line = lines[0] if lines else ""

headers = {}
for line in lines[1:]:
    if ":" not in line:
        continue
    key, value = line.split(":", 1)
    headers[key.strip().lower()] = value.strip()

metadata = {
    "platform": platform,
    "url": url,
    "effective_url": metrics.get("effective_url"),
    "http_status": int(metrics.get("http_code") or 0),
    "content_type": metrics.get("content_type") or headers.get("content-type"),
    "size_download": int(float(metrics.get("size_download") or 0)),
    "status_line": status_line,
    "headers": {
        key: headers[key]
        for key in [
            "content-type",
            "content-length",
            "content-disposition",
            "etag",
            "last-modified",
            "date",
            "server",
        ]
        if key in headers
    },
}

Path(output_path).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
