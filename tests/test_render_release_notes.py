import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_release_notes import render_release_notes


class RenderReleaseNotesTests(unittest.TestCase):
    def test_release_notes_include_identity_hashes_and_limitations(self):
        manifest = {
            "captured_at": "2026-05-30T12:34:56Z",
            "source_page": "https://openai.com/codex/",
            "release": {
                "tag": "desktop-v26.527.31326",
                "title": "Codex Desktop 26.527.31326",
                "evidence_level": "strong",
            },
            "artifacts": [
                {
                    "platform": "macos",
                    "classification": "full-installer",
                    "sha256": "mac-sha",
                    "size": 400814855,
                    "source": {"url": "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg"},
                    "app": {"version": "26.527.31326", "build": "3390"},
                    "dmg": {"top_level_entries": ["Applications", "Codex.app"], "external_payloads": []},
                    "verification": {"passed": True, "team_id": "2DC432GLL2"},
                }
            ],
            "limitations": ["This project is not affiliated with OpenAI."],
        }

        notes = render_release_notes(manifest)

        self.assertIn("# Codex Desktop 26.527.31326", notes)
        self.assertIn("Evidence level: `strong`", notes)
        self.assertIn("macos", notes)
        self.assertIn("mac-sha", notes)
        self.assertIn("2DC432GLL2", notes)
        self.assertIn("DMG top-level entries", notes)
        self.assertIn("External DMG payloads: none", notes)
        self.assertIn("This project is not affiliated with OpenAI.", notes)


if __name__ == "__main__":
    unittest.main()
