#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <codex-dmg> <inspection-output-json>" >&2
  exit 64
fi

dmg_path="$1"
output_path="$2"
expected_bundle_id="com.openai.codex"
expected_name="Codex"
expected_executable="Codex"
expected_team_id="2DC432GLL2"
expected_origin="Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)"

tmpdir="$(mktemp -d)"
mount_root="$tmpdir/mount"
mkdir -p "$mount_root" "$(dirname "$output_path")"

detach() {
  hdiutil detach "$mount_root" -quiet >/dev/null 2>&1 || true
  rm -rf "$tmpdir"
}
trap detach EXIT

hdiutil_log="$tmpdir/hdiutil.log"
codesign_verify_log="$tmpdir/codesign-verify.log"
codesign_details_log="$tmpdir/codesign-details.log"
spctl_log="$tmpdir/spctl.log"
stapler_log="$tmpdir/stapler.log"
top_level_entries_file="$tmpdir/top-level-entries.txt"
external_payloads_file="$tmpdir/external-payloads.txt"

hdiutil_passed=false
codesign_passed=false
spctl_passed=false
stapler_passed=false

if hdiutil verify "$dmg_path" >"$hdiutil_log" 2>&1; then
  hdiutil_passed=true
fi

hdiutil attach -readonly -nobrowse -mountpoint "$mount_root" "$dmg_path" >/dev/null

app_count="$(find "$mount_root" -maxdepth 2 -type d -name '*.app' -print | wc -l | tr -d ' ')"
app_path="$(find "$mount_root" -maxdepth 2 -type d -name 'Codex.app' -print -quit)"
if [ -z "$app_path" ]; then
  echo "No Codex.app bundle found in DMG" >&2
  exit 1
fi

find "$mount_root" -mindepth 1 -maxdepth 1 -exec basename {} \; | LC_ALL=C sort > "$top_level_entries_file"
: > "$external_payloads_file"
while IFS= read -r payload_path; do
  case "$payload_path" in
    "$app_path"|"$app_path"/*) continue ;;
  esac

  relative_path="${payload_path#"$mount_root"/}"
  payload_name="$(basename "$payload_path")"
  case "$payload_name" in
    *.app|*.pkg|*.mpkg|*.command|*.tool|*.sh|*.bash|*.zsh|*.py|*.rb|*.pl|*.js|*.scpt)
      printf '%s\n' "$relative_path" >> "$external_payloads_file"
      continue
      ;;
  esac

  if [ -f "$payload_path" ] && [ -x "$payload_path" ]; then
    printf '%s\n' "$relative_path" >> "$external_payloads_file"
  fi
done < <(find "$mount_root" -mindepth 1 -print)
LC_ALL=C sort -u "$external_payloads_file" -o "$external_payloads_file"

plist="$app_path/Contents/Info.plist"
bundle_id="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$plist" 2>/dev/null || true)"
name="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "$plist" 2>/dev/null || true)"
executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$plist" 2>/dev/null || true)"
version="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$plist" 2>/dev/null || true)"
build="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$plist" 2>/dev/null || true)"

if codesign --verify --verbose=4 "$app_path" >"$codesign_verify_log" 2>&1; then
  codesign_passed=true
fi
codesign -dv --verbose=4 "$app_path" >"$codesign_details_log" 2>&1 || true

if spctl -a -vv -t exec "$app_path" >"$spctl_log" 2>&1; then
  spctl_passed=true
fi

if xcrun stapler validate "$app_path" >"$stapler_log" 2>&1; then
  stapler_passed=true
fi

team_id="$(grep '^TeamIdentifier=' "$codesign_details_log" | head -n 1 | cut -d= -f2- || true)"
origin="$(grep '^Authority=Developer ID Application:' "$codesign_details_log" | head -n 1 | cut -d= -f2- || true)"

python3 - "$output_path" \
  "$bundle_id" "$name" "$executable" "$version" "$build" "$team_id" "$origin" "$app_count" \
  "$expected_bundle_id" "$expected_name" "$expected_executable" "$expected_team_id" "$expected_origin" \
  "$hdiutil_passed" "$codesign_passed" "$spctl_passed" "$stapler_passed" \
  "$hdiutil_log" "$codesign_verify_log" "$codesign_details_log" "$spctl_log" "$stapler_log" \
  "$top_level_entries_file" "$external_payloads_file" <<'PY'
import json
import sys
from pathlib import Path

(
    output_path,
    bundle_id,
    name,
    executable,
    version,
    build,
    team_id,
    origin,
    app_count,
    expected_bundle_id,
    expected_name,
    expected_executable,
    expected_team_id,
    expected_origin,
    hdiutil_passed,
    codesign_passed,
    spctl_passed,
    stapler_passed,
    hdiutil_log,
    codesign_verify_log,
    codesign_details_log,
    spctl_log,
    stapler_log,
    top_level_entries_file,
    external_payloads_file,
) = sys.argv[1:]

def as_bool(value):
    return value == "true"

logs = {
    "hdiutil": Path(hdiutil_log).read_text(encoding="utf-8", errors="replace").strip(),
    "codesign_verify": Path(codesign_verify_log).read_text(encoding="utf-8", errors="replace").strip(),
    "codesign_details": Path(codesign_details_log).read_text(encoding="utf-8", errors="replace").strip(),
    "spctl": Path(spctl_log).read_text(encoding="utf-8", errors="replace").strip(),
    "stapler": Path(stapler_log).read_text(encoding="utf-8", errors="replace").strip(),
}

allowed_top_level_entries = {
    "Applications",
    "Codex.app",
    ".background",
    ".DS_Store",
    ".fseventsd",
    ".Trashes",
    ".VolumeIcon.icns",
    "Icon",
    "Icon\r",
}
top_level_entries = [
    line
    for line in Path(top_level_entries_file).read_text(encoding="utf-8", errors="replace").splitlines()
    if line
]
unexpected_top_level_entries = [
    entry for entry in top_level_entries if entry not in allowed_top_level_entries
]
external_payloads = [
    line
    for line in Path(external_payloads_file).read_text(encoding="utf-8", errors="replace").splitlines()
    if line
]

checks = {
    "hdiutil_verify": as_bool(hdiutil_passed),
    "codesign_verify": as_bool(codesign_passed),
    "spctl_assessment": as_bool(spctl_passed),
    "stapler_validate": as_bool(stapler_passed),
    "expected_bundle_id": bundle_id == expected_bundle_id,
    "expected_name": name == expected_name,
    "expected_executable": executable == expected_executable,
    "expected_single_app": app_count == "1",
    "expected_team_id": team_id == expected_team_id,
    "expected_origin": origin == expected_origin,
    "expected_volume_top_level": not unexpected_top_level_entries,
    "no_external_payloads": not external_payloads,
}

result = {
    "classification": "full-installer",
    "app": {
        "bundle_id": bundle_id or None,
        "name": name or None,
        "executable": executable or None,
        "version": version or None,
        "build": build or None,
        "app_count": int(app_count or 0),
    },
    "dmg": {
        "top_level_entries": top_level_entries,
        "unexpected_top_level_entries": unexpected_top_level_entries,
        "external_payloads": external_payloads,
    },
    "verification": {
        "passed": all(checks.values()),
        "team_id": team_id or None,
        "origin": origin or None,
        "expected_bundle_id": expected_bundle_id,
        "expected_name": expected_name,
        "expected_executable": expected_executable,
        "expected_team_id": expected_team_id,
        "expected_origin": expected_origin,
        "checks": checks,
        "logs": logs,
    },
}

Path(output_path).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if not result["verification"]["passed"]:
    raise SystemExit(1)
PY
