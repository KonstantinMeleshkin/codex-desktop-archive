#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <manifest-json> <release-notes-md>" >&2
  exit 64
fi

manifest_path="$1"
release_notes_path="$2"
tmpdir="$(mktemp -d)"

cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

read_manifest_field() {
  python3 - "$manifest_path" "$1" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = manifest
for part in sys.argv[2].split("."):
    if isinstance(value, list):
        value = value[int(part)]
    else:
        value = value[part]
print(value)
PY
}

verify_tag_target() {
  local tag="$1"
  local expected_sha="$2"
  local actual_sha

  git fetch --tags --force >/dev/null
  actual_sha="$(git rev-list -n 1 "$tag" 2>/dev/null || true)"
  if [ -z "$actual_sha" ]; then
    echo "Expected release tag ${tag} does not exist." >&2
    exit 1
  fi
  if [ "$actual_sha" != "$expected_sha" ]; then
    echo "Release tag ${tag} points to ${actual_sha}, expected ${expected_sha}." >&2
    exit 1
  fi
}

tag="$(read_manifest_field release.tag)"
target_sha="$(read_manifest_field workflow.commit_sha)"

python3 scripts/release_guard.py validate-manifest --manifest "$manifest_path"

if ! gh release view "$tag" >/dev/null 2>&1; then
  echo "Expected existing release ${tag} was not found." >&2
  exit 1
fi

existing_assets="$tmpdir/existing-assets"
mkdir -p "$existing_assets"
gh release download "$tag" --dir "$existing_assets"
python3 scripts/release_guard.py verify-assets \
  --manifest "$manifest_path" \
  --asset-dir "$existing_assets" \
  --require-manifest-asset \
  --release-notes "$release_notes_path"
verify_tag_target "$tag" "$target_sha"

echo "Existing release ${tag} assets, manifest, release notes, and tag target verified."
