import sys
import tempfile
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from release_guard import (
    SecurityPolicyError,
    validate_manifest,
    verify_asset_directory,
    verify_local_artifact,
)


MAC_SHA = "370a76cf980208943e85e7b19eb24155e060585a7ee69e8a50db622697883347"


def valid_manifest():
    return {
        "schema_version": "1.0",
        "captured_at": "2026-05-30T12:34:56Z",
        "source_page": "https://openai.com/codex/",
        "repository": "KonstantinMeleshkin/codex-desktop-archive",
        "workflow": {"run_id": "123", "commit_sha": "a" * 40},
        "release": {
            "tag": "desktop-v26.527.31326",
            "title": "Codex Desktop 26.527.31326",
            "identity": {"product": "codex-desktop", "version": "26.527.31326", "build": "3390"},
            "evidence_level": "strong",
        },
        "artifacts": [
            {
                "platform": "macos",
                "classification": "full-installer",
                "filename": "Codex-Desktop-26.527.31326-macos.dmg",
                "sha256": MAC_SHA,
                "size": 13,
                "source": {
                    "url": "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg",
                    "effective_url": "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg",
                    "http_status": 200,
                    "headers": {"content-type": "application/x-apple-diskimage"},
                },
                "app": {
                    "bundle_id": "com.openai.codex",
                    "name": "Codex",
                    "executable": "Codex",
                    "app_count": 1,
                    "version": "26.527.31326",
                    "build": "3390",
                },
                "dmg": {
                    "top_level_entries": ["Applications", "Codex.app"],
                    "unexpected_top_level_entries": [],
                    "external_payloads": [],
                },
                "verification": {
                    "passed": True,
                    "team_id": "2DC432GLL2",
                    "origin": "Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)",
                    "checks": {
                        "hdiutil_verify": True,
                        "codesign_verify": True,
                        "spctl_assessment": True,
                        "stapler_validate": True,
                        "expected_bundle_id": True,
                        "expected_name": True,
                        "expected_executable": True,
                        "expected_single_app": True,
                        "expected_team_id": True,
                        "expected_origin": True,
                        "expected_volume_top_level": True,
                        "no_external_payloads": True,
                    },
                },
            }
        ],
        "limitations": [],
    }


def valid_inspection():
    artifact = valid_manifest()["artifacts"][0]
    return {
        "classification": artifact["classification"],
        "app": artifact["app"],
        "dmg": artifact["dmg"],
        "verification": artifact["verification"],
    }


class ReleaseGuardTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        validate_manifest(valid_manifest())

    def test_rejects_any_second_artifact(self):
        manifest = valid_manifest()
        manifest["artifacts"].append({"platform": "other", "classification": "unsupported"})

        with self.assertRaisesRegex(SecurityPolicyError, "exactly one macOS artifact"):
            validate_manifest(manifest)

    def test_rejects_unsafe_release_tag(self):
        manifest = valid_manifest()
        manifest["release"]["tag"] = "desktop-v26.527.31326\nbad"

        with self.assertRaisesRegex(SecurityPolicyError, "unsafe release tag"):
            validate_manifest(manifest)

    def test_rejects_unsafe_workflow_commit_sha(self):
        manifest = valid_manifest()
        manifest["workflow"]["commit_sha"] = "abc123\nbad"

        with self.assertRaisesRegex(SecurityPolicyError, "workflow commit SHA"):
            validate_manifest(manifest)

    def test_rejects_wrong_macos_bundle_id(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["app"]["bundle_id"] = "com.openai.other"

        with self.assertRaisesRegex(SecurityPolicyError, "macOS bundle id"):
            validate_manifest(manifest)

    def test_rejects_failed_verification_flag(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["verification"]["checks"]["spctl_assessment"] = False

        with self.assertRaisesRegex(SecurityPolicyError, "macOS verification checks"):
            validate_manifest(manifest)

    def test_rejects_unexpected_dmg_top_level_entries(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["dmg"]["top_level_entries"].append("Install.command")
        manifest["artifacts"][0]["dmg"]["unexpected_top_level_entries"].append("Install.command")
        manifest["artifacts"][0]["verification"]["checks"]["expected_volume_top_level"] = False

        with self.assertRaisesRegex(SecurityPolicyError, "unexpected DMG top-level"):
            validate_manifest(manifest)

    def test_rejects_external_dmg_payloads(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["dmg"]["external_payloads"].append("hidden/helper.sh")
        manifest["artifacts"][0]["verification"]["checks"]["no_external_payloads"] = False

        with self.assertRaisesRegex(SecurityPolicyError, "external DMG payload"):
            validate_manifest(manifest)

    def test_rejects_unexpected_source_url(self):
        manifest = valid_manifest()
        manifest["artifacts"][0]["source"]["effective_url"] = "https://example.com/Codex.dmg"

        with self.assertRaisesRegex(SecurityPolicyError, "macOS effective URL"):
            validate_manifest(manifest)

    def test_verify_asset_directory_checks_hashes(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Codex-Desktop-26.527.31326-macos.dmg").write_bytes(b"codex desktop")
            verify_asset_directory(manifest, root, require_manifest_asset=False)

    def test_verify_asset_directory_rejects_extra_assets(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Codex-Desktop-26.527.31326-macos.dmg").write_bytes(b"codex desktop")
            (root / "unexpected.dmg").write_text("bad", encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "unexpected release asset"):
                verify_asset_directory(manifest, root, require_manifest_asset=False)

    def test_verify_asset_directory_rejects_swapped_release_notes(self):
        manifest = valid_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            expected_notes = root / "expected-release-notes.md"
            expected_notes.write_text("trusted notes\n", encoding="utf-8")
            (asset_dir / "Codex-Desktop-26.527.31326-macos.dmg").write_bytes(b"codex desktop")
            (asset_dir / "codex-desktop-manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (asset_dir / "release-notes.md").write_text("changed notes\n", encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "release notes asset"):
                verify_asset_directory(
                    manifest,
                    asset_dir,
                    require_manifest_asset=True,
                    release_notes_path=expected_notes,
                )

    def test_verify_local_artifact_accepts_matching_fresh_inspection(self):
        manifest = valid_manifest()
        inspection = valid_inspection()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "Codex-Desktop-26.527.31326-macos.dmg"
            inspection_path = root / "inspection.json"
            artifact.write_bytes(b"codex desktop")
            inspection_path.write_text(json.dumps(inspection), encoding="utf-8")

            verify_local_artifact(manifest, artifact, inspection_path)

    def test_verify_local_artifact_rejects_publish_side_inspection_mismatch(self):
        manifest = valid_manifest()
        inspection = valid_inspection()
        inspection["app"]["bundle_id"] = "com.openai.other"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "Codex-Desktop-26.527.31326-macos.dmg"
            inspection_path = root / "inspection.json"
            artifact.write_bytes(b"codex desktop")
            inspection_path.write_text(json.dumps(inspection), encoding="utf-8")

            with self.assertRaisesRegex(SecurityPolicyError, "fresh macOS inspection"):
                verify_local_artifact(manifest, artifact, inspection_path)


if __name__ == "__main__":
    unittest.main()
