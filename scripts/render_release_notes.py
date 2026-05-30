#!/usr/bin/env python3
"""Render GitHub release notes from a Codex Desktop manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _artifact_section(artifact: dict[str, Any]) -> str:
    app = artifact.get("app") or {}
    dmg = artifact.get("dmg") or {}
    verification = artifact.get("verification") or {}
    source = artifact.get("source") or {}
    lines = [
        f"### {artifact.get('platform', 'unknown')}",
        "",
        f"- Classification: `{artifact.get('classification', 'unknown')}`",
        f"- SHA-256: `{artifact.get('sha256')}`",
        f"- Size: `{artifact.get('size')}` bytes",
    ]
    if source.get("url"):
        lines.append(f"- Source URL: {source['url']}")
    if app.get("version"):
        lines.append(f"- App version: `{app['version']}`")
    if app.get("build"):
        lines.append(f"- App build: `{app['build']}`")
    if verification:
        lines.append(f"- Verification passed: `{bool(verification.get('passed'))}`")
    if verification.get("team_id"):
        lines.append(f"- Signing Team ID: `{verification['team_id']}`")
    if dmg.get("top_level_entries"):
        entries = ", ".join(f"`{entry}`" for entry in dmg["top_level_entries"])
        lines.append(f"- DMG top-level entries: {entries}")
    if "external_payloads" in dmg:
        payloads = dmg.get("external_payloads") or []
        value = "none" if not payloads else ", ".join(f"`{item}`" for item in payloads)
        lines.append(f"- External DMG payloads: {value}")
    return "\n".join(lines)


def render_release_notes(manifest: dict[str, Any]) -> str:
    release = manifest.get("release", {})
    limitations = manifest.get("limitations", [])
    sections = [
        f"# {release.get('title', 'Codex Desktop capture')}",
        "",
        f"- Captured at: `{manifest.get('captured_at')}`",
        f"- Evidence level: `{release.get('evidence_level', 'unknown')}`",
        f"- Source page: {manifest.get('source_page')}",
        "",
        "## Artifacts",
        "",
        "\n\n".join(_artifact_section(artifact) for artifact in manifest.get("artifacts", [])),
        "",
        "## Limitations",
        "",
    ]
    sections.extend(f"- {item}" for item in limitations)
    sections.append("")
    sections.append("See `codex-desktop-manifest.json` attached to this release for full machine-readable evidence.")
    sections.append("")
    return "\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render release notes from a manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.manifest.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_release_notes(manifest), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
