#!/usr/bin/env python3
"""Fail-closed release policy checks for Codex Desktop archive publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MACOS_URL = "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg"
EXPECTED_BUNDLE_ID = "com.openai.codex"
EXPECTED_APP_NAME = "Codex"
EXPECTED_EXECUTABLE = "Codex"
EXPECTED_TEAM_ID = "2DC432GLL2"
EXPECTED_ORIGIN = "Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)"
REQUIRED_VERIFICATION_CHECKS = [
    "hdiutil_verify",
    "codesign_verify",
    "spctl_assessment",
    "stapler_validate",
    "expected_bundle_id",
    "expected_name",
    "expected_executable",
    "expected_single_app",
    "expected_team_id",
    "expected_origin",
    "expected_volume_top_level",
    "no_external_payloads",
]


class SecurityPolicyError(ValueError):
    """Raised when a release candidate violates archive security policy."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SecurityPolicyError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _macos_artifact(manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest.get("artifacts", [])
    _require(len(artifacts) == 1, "manifest must contain exactly one macOS artifact")
    artifact = artifacts[0]
    _require(artifact.get("platform") == "macos", "manifest must contain exactly one macOS artifact")
    _require(artifact.get("classification") == "full-installer", "macOS artifact must be a full installer")
    return artifact


def _validate_source(source: dict[str, Any]) -> None:
    _require(source.get("url") == MACOS_URL, "macOS source URL is not the approved official URL")
    effective_url = source.get("effective_url")
    _require(effective_url == MACOS_URL, "macOS effective URL is not the approved official URL")
    parsed = urlparse(effective_url or "")
    _require(parsed.scheme == "https", "macOS effective URL must use https")
    _require(parsed.netloc == "persistent.oaistatic.com", "macOS effective URL host is not approved")
    _require(parsed.path == "/codex-app-prod/Codex.dmg", "macOS effective URL path is not approved")
    _require(source.get("http_status") == 200, "macOS source HTTP status must be 200")
    content_type = (source.get("headers") or {}).get("content-type") or source.get("content_type") or ""
    _require("apple-diskimage" in content_type, "macOS content type must be an Apple disk image")


def _validate_macos_payload(payload: dict[str, Any], version: str, build: str, *, label: str) -> None:
    _require(payload.get("classification") == "full-installer", f"{label} must be a full installer")

    app = payload.get("app") or {}
    _require(app.get("bundle_id") == EXPECTED_BUNDLE_ID, f"{label} bundle id does not match Codex")
    _require(app.get("name") == EXPECTED_APP_NAME, f"{label} app name does not match Codex")
    _require(app.get("executable") == EXPECTED_EXECUTABLE, f"{label} executable does not match Codex")
    _require(app.get("app_count") == 1, f"{label} DMG must contain exactly one app bundle")
    _require(app.get("version") == version, f"{label} app version does not match release identity")
    _require(app.get("build") == build, f"{label} app build does not match release identity")

    dmg = payload.get("dmg") or {}
    top_level_entries = dmg.get("top_level_entries")
    unexpected_entries = dmg.get("unexpected_top_level_entries")
    external_payloads = dmg.get("external_payloads")
    _require(isinstance(top_level_entries, list), f"{label} DMG inventory is missing")
    _require(unexpected_entries == [], f"{label} has unexpected DMG top-level entries")
    _require(external_payloads == [], f"{label} has external DMG payloads")

    verification = payload.get("verification") or {}
    checks = verification.get("checks") or {}
    _require(verification.get("passed") is True, f"{label} verification did not pass")
    _require(verification.get("team_id") == EXPECTED_TEAM_ID, f"{label} signing Team ID does not match OpenAI")
    _require(verification.get("origin") == EXPECTED_ORIGIN, f"{label} signing origin does not match OpenAI")
    _require(
        all(checks.get(name) is True for name in REQUIRED_VERIFICATION_CHECKS),
        f"{label} verification checks did not all pass",
    )


def validate_manifest(manifest: dict[str, Any]) -> None:
    release = manifest.get("release") or {}
    identity = release.get("identity") or {}
    workflow = manifest.get("workflow") or {}
    tag = release.get("tag")
    version = identity.get("version")
    build = identity.get("build")

    _require(manifest.get("schema_version") == "1.0", "unsupported manifest schema")
    _require(
        re.fullmatch(r"[a-f0-9]{40}", workflow.get("commit_sha") or "") is not None,
        "workflow commit SHA is invalid",
    )
    _require(release.get("evidence_level") == "strong", "macOS-only releases must have strong evidence")
    _require(isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version), "unsafe app version")
    _require(isinstance(build, str) and re.fullmatch(r"[A-Za-z0-9._-]+", build), "unsafe app build")
    _require(tag == f"desktop-v{version}", "unsafe release tag")
    _require(re.fullmatch(r"desktop-v\d+\.\d+\.\d+", tag or ""), "unsafe release tag")

    artifact = _macos_artifact(manifest)
    expected_filename = f"Codex-Desktop-{version}-macos.dmg"
    _require(artifact.get("filename") == expected_filename, "macOS release filename does not match version")
    _require(re.fullmatch(r"[a-f0-9]{64}", artifact.get("sha256") or ""), "macOS SHA-256 is invalid")
    _require(isinstance(artifact.get("size"), int) and artifact["size"] > 0, "macOS artifact size is invalid")

    _validate_source(artifact.get("source") or {})

    _validate_macos_payload(artifact, version, build, label="macOS")


def verify_asset_directory(
    manifest: dict[str, Any],
    asset_dir: Path,
    *,
    require_manifest_asset: bool,
    release_notes_path: Path | None = None,
) -> None:
    validate_manifest(manifest)
    artifact = _macos_artifact(manifest)
    expected_files = {artifact["filename"]}
    if require_manifest_asset:
        expected_files.update({"codex-desktop-manifest.json", "release-notes.md"})

    actual_files = {path.name for path in asset_dir.iterdir() if path.is_file()}
    extra_files = actual_files - expected_files
    missing_files = expected_files - actual_files
    _require(not extra_files, f"unexpected release asset(s): {', '.join(sorted(extra_files))}")
    _require(not missing_files, f"missing release asset(s): {', '.join(sorted(missing_files))}")

    artifact_path = asset_dir / artifact["filename"]
    _require(artifact_path.stat().st_size == artifact["size"], "macOS release asset size does not match manifest")
    _require(_sha256(artifact_path) == artifact["sha256"], "macOS release asset SHA-256 does not match manifest")

    if require_manifest_asset:
        attached_manifest = json.loads((asset_dir / "codex-desktop-manifest.json").read_text(encoding="utf-8"))
        _require(attached_manifest == manifest, "attached manifest does not match candidate manifest")
    if release_notes_path is not None:
        _require(
            (asset_dir / "release-notes.md").read_bytes() == release_notes_path.read_bytes(),
            "release notes asset does not match expected release notes",
        )


def verify_local_artifact(manifest: dict[str, Any], artifact_path: Path, inspection_path: Path) -> None:
    validate_manifest(manifest)
    artifact = _macos_artifact(manifest)
    version = manifest["release"]["identity"]["version"]
    build = manifest["release"]["identity"]["build"]

    _require(artifact_path.stat().st_size == artifact["size"], "local macOS artifact size does not match manifest")
    _require(_sha256(artifact_path) == artifact["sha256"], "local macOS artifact SHA-256 does not match manifest")

    inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
    _validate_macos_payload(inspection, version, build, label="fresh macOS inspection")

    _require(inspection.get("classification") == artifact.get("classification"), "fresh macOS inspection does not match manifest")
    _require(inspection.get("app") == artifact.get("app"), "fresh macOS inspection does not match manifest")
    _require(inspection.get("dmg") == artifact.get("dmg"), "fresh macOS inspection does not match manifest")

    inspection_verification = inspection.get("verification") or {}
    artifact_verification = artifact.get("verification") or {}
    for key in [
        "passed",
        "team_id",
        "origin",
        "expected_bundle_id",
        "expected_name",
        "expected_executable",
        "expected_team_id",
        "expected_origin",
        "checks",
    ]:
        _require(
            inspection_verification.get(key) == artifact_verification.get(key),
            "fresh macOS inspection does not match manifest",
        )


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Codex Desktop release security invariants.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser("validate-manifest")
    manifest_parser.add_argument("--manifest", type=Path, required=True)

    assets_parser = subparsers.add_parser("verify-assets")
    assets_parser.add_argument("--manifest", type=Path, required=True)
    assets_parser.add_argument("--asset-dir", type=Path, required=True)
    assets_parser.add_argument("--require-manifest-asset", action="store_true")
    assets_parser.add_argument("--release-notes", type=Path)

    local_parser = subparsers.add_parser("verify-local-artifact")
    local_parser.add_argument("--manifest", type=Path, required=True)
    local_parser.add_argument("--artifact", type=Path, required=True)
    local_parser.add_argument("--inspection", type=Path, required=True)

    args = parser.parse_args()
    manifest = _load_manifest(args.manifest)

    if args.command == "validate-manifest":
        validate_manifest(manifest)
    elif args.command == "verify-assets":
        verify_asset_directory(
            manifest,
            args.asset_dir,
            require_manifest_asset=args.require_manifest_asset,
            release_notes_path=args.release_notes,
        )
    elif args.command == "verify-local-artifact":
        verify_local_artifact(manifest, args.artifact, args.inspection)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
