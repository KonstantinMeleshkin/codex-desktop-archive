import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_manifest import build_manifest, file_identity, release_identity


class ManifestTests(unittest.TestCase):
    def test_file_identity_records_sha256_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Codex.dmg"
            path.write_bytes(b"codex desktop")

            identity = file_identity(path)

        self.assertEqual(identity["sha256"], "370a76cf980208943e85e7b19eb24155e060585a7ee69e8a50db622697883347")
        self.assertEqual(identity["size"], 13)

    def test_release_identity_prefers_macos_app_version(self):
        artifact = {
            "platform": "macos",
            "app": {"version": "26.527.31326", "build": "3390"},
        }

        identity = release_identity([artifact], "2026-05-30T00:00:00Z")

        self.assertEqual(identity["tag"], "desktop-v26.527.31326")
        self.assertEqual(identity["title"], "Codex Desktop 26.527.31326")
        self.assertEqual(identity["identity"]["version"], "26.527.31326")

    def test_release_identity_falls_back_to_capture_date(self):
        artifact = {"platform": "macos", "classification": "full-installer"}

        identity = release_identity([artifact], "2026-05-30T12:34:56Z")

        self.assertEqual(identity["tag"], "desktop-capture-2026-05-30")
        self.assertEqual(identity["evidence_level"], "partial")

    def test_build_manifest_contains_sources_artifacts_and_limitations(self):
        artifact = {
            "platform": "macos",
            "classification": "full-installer",
            "sha256": "mac-sha",
            "size": 400814855,
            "source": {"url": "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg"},
            "app": {"version": "26.527.31326", "build": "3390"},
            "verification": {"passed": True, "team_id": "2DC432GLL2"},
        }

        manifest = build_manifest(
            captured_at="2026-05-30T12:34:56Z",
            repository="KonstantinMeleshkin/codex-desktop-archive",
            workflow_run_id="123",
            workflow_sha="abcdef",
            artifacts=[artifact],
        )

        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["repository"], "KonstantinMeleshkin/codex-desktop-archive")
        self.assertEqual(manifest["release"]["tag"], "desktop-v26.527.31326")
        self.assertEqual(manifest["artifacts"][0]["filename"], "Codex-Desktop-26.527.31326-macos.dmg")
        self.assertEqual(manifest["artifacts"][0]["platform"], "macos")
        self.assertIn("This project is not affiliated with OpenAI.", manifest["limitations"])


if __name__ == "__main__":
    unittest.main()
