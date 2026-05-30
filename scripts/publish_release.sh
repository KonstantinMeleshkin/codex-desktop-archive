#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "usage: $0 <manifest-json> <release-notes-md> <macos-artifact> <fresh-inspection-json>" >&2
  exit 64
fi

manifest_path="$1"
release_notes_path="$2"
artifact_path="$3"
inspection_path="$4"

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

commit_manifest() {
  local tag="$1"
  local history_path="manifest/history/${tag}.json"

  mkdir -p manifest/history
  cp "$manifest_path" "$history_path"
  cp "$manifest_path" manifest/latest.json

  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git add manifest/latest.json "$history_path"

  if ! git diff --cached --quiet; then
    git commit -m "Archive ${tag}"
    git push
  fi
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

publish_draft_if_needed() {
  local tag="$1"
  local is_draft

  is_draft="$(gh release view "$tag" --json isDraft --jq '.isDraft')"
  if [ "$is_draft" = "true" ]; then
    gh release edit "$tag" --draft=false
  fi
}

ensure_release_tag() {
  local tag="$1"
  local expected_sha="$2"

  git fetch --tags --force >/dev/null
  if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
    verify_tag_target "$tag" "$expected_sha"
    return
  fi

  git tag "$tag" "$expected_sha"
  git push origin "refs/tags/${tag}"
  verify_tag_target "$tag" "$expected_sha"
}

tag="$(read_manifest_field release.tag)"
title="$(read_manifest_field release.title)"
target_sha="$(read_manifest_field workflow.commit_sha)"
artifact_filename="$(read_manifest_field artifacts.0.filename)"

python3 scripts/release_guard.py validate-manifest --manifest "$manifest_path"

staged_assets="$tmpdir/new-assets"
mkdir -p "$staged_assets"

if [ ! -f "$artifact_path" ]; then
  echo "Missing release artifact: $artifact_path" >&2
  exit 1
fi
if [ ! -f "$inspection_path" ]; then
  echo "Missing fresh macOS inspection: $inspection_path" >&2
  exit 1
fi

python3 scripts/release_guard.py verify-local-artifact \
  --manifest "$manifest_path" \
  --artifact "$artifact_path" \
  --inspection "$inspection_path"

cp "$artifact_path" "$staged_assets/$artifact_filename"
cp "$manifest_path" "$staged_assets/codex-desktop-manifest.json"
cp "$release_notes_path" "$staged_assets/release-notes.md"
python3 scripts/release_guard.py verify-assets \
  --manifest "$manifest_path" \
  --asset-dir "$staged_assets" \
  --require-manifest-asset \
  --release-notes "$release_notes_path"

if gh release view "$tag" >/dev/null 2>&1; then
  existing_assets="$tmpdir/existing-assets"
  mkdir -p "$existing_assets"
  gh release download "$tag" --dir "$existing_assets"
  python3 scripts/release_guard.py verify-assets \
    --manifest "$manifest_path" \
    --asset-dir "$existing_assets" \
    --require-manifest-asset \
    --release-notes "$release_notes_path"
  verify_tag_target "$tag" "$target_sha"
  publish_draft_if_needed "$tag"
  commit_manifest "$tag"
  echo "Release ${tag} already exists with verified assets; repository manifest is current."
  exit 0
fi

ensure_release_tag "$tag" "$target_sha"

gh release create "$tag" \
  "$staged_assets/$artifact_filename" \
  "$staged_assets/codex-desktop-manifest.json" \
  "$staged_assets/release-notes.md" \
  --draft \
  --title "$title" \
  --notes-file "$release_notes_path"

verify_tag_target "$tag" "$target_sha"

published_assets="$tmpdir/published-assets"
mkdir -p "$published_assets"
gh release download "$tag" --dir "$published_assets"
python3 scripts/release_guard.py verify-assets \
  --manifest "$manifest_path" \
  --asset-dir "$published_assets" \
  --require-manifest-asset \
  --release-notes "$release_notes_path"

publish_draft_if_needed "$tag"
commit_manifest "$tag"
