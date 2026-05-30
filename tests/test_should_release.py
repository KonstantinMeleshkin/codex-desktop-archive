import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from should_release import decide_release


def manifest(tag, mac_sha, mac_version="26.527.31326"):
    return {
        "schema_version": "1.0",
        "release": {
            "tag": tag,
            "title": f"Codex Desktop {mac_version}",
            "identity": {
                "product": "codex-desktop",
                "version": mac_version,
                "build": "3390",
            },
        },
        "artifacts": [
            {
                "platform": "macos",
                "classification": "full-installer",
                "sha256": mac_sha,
                "size": 400814855,
                "app": {"version": mac_version, "build": "3390"},
            },
        ],
    }


class DecideReleaseTests(unittest.TestCase):
    def test_releases_when_no_latest_manifest_exists(self):
        candidate = manifest("desktop-v26.527.31326", "mac-sha")

        decision = decide_release(None, candidate)

        self.assertTrue(decision["should_release"])
        self.assertEqual(decision["tag"], "desktop-v26.527.31326")
        self.assertEqual(decision["reason"], "no previous manifest")

    def test_skips_when_all_platform_identities_match(self):
        latest = manifest("desktop-v26.527.31326", "mac-sha")
        candidate = manifest("desktop-v26.527.31326", "mac-sha")

        decision = decide_release(latest, candidate)

        self.assertFalse(decision["should_release"])
        self.assertEqual(decision["reason"], "all artifact identities unchanged")

    def test_releases_when_macos_hash_changes_even_if_version_matches(self):
        latest = manifest("desktop-v26.527.31326", "old-mac-sha")
        candidate = manifest("desktop-v26.527.31326", "new-mac-sha")

        decision = decide_release(latest, candidate)

        self.assertTrue(decision["should_release"])
        self.assertIn("macos sha256 changed", decision["reason"])


if __name__ == "__main__":
    unittest.main()
