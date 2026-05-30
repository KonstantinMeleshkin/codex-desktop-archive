#!/usr/bin/env python3
"""Build release manifests for the Codex Desktop archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
SOURCE_PAGE = "https://openai.com/codex/"
MACOS_URL = "https://persistent.oaistatic.com/codex-app-prod/Codex.dmg"

LIMITATIONS = [
    "This project is not affiliated with OpenAI.",
    "Artifacts are archived from official OpenAI-linked download URLs.",
    "Historical byte identity cannot be proven without an OpenAI-published historical hash.",
    "This archive supports macOS Codex Desktop only.",
]


def file_identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size": size}


def release_identity(artifacts: list[dict[str, Any]], captured_at: str) -> dict[str, Any]:
    macos = next((item for item in artifacts if item.get("platform") == "macos"), None)
    app = (macos or {}).get("app") or {}
    version = app.get("version")
    build = app.get("build")

    if version:
        identity = {
            "product": "codex-desktop",
            "version": version,
            "build": build,
        }
        return {
            "tag": f"desktop-v{version}",
            "title": f"Codex Desktop {version}",
            "identity": identity,
            "evidence_level": "strong",
        }

    capture_date = captured_at[:10]
    return {
        "tag": f"desktop-capture-{capture_date}",
        "title": f"Codex Desktop capture {capture_date}",
        "identity": {
            "product": "codex-desktop",
            "version": None,
            "build": None,
        },
        "evidence_level": "partial",
    }


def build_manifest(
    *,
    captured_at: str,
    repository: str,
    workflow_run_id: str,
    workflow_sha: str,
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    sorted_artifacts = sorted(artifacts, key=lambda item: item.get("platform", ""))
    release = release_identity(sorted_artifacts, captured_at)
    version = release["identity"].get("version")
    if version:
        for artifact in sorted_artifacts:
            if artifact.get("platform") == "macos":
                artifact["filename"] = f"Codex-Desktop-{version}-macos.dmg"

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "source_page": SOURCE_PAGE,
        "repository": repository,
        "workflow": {
            "run_id": workflow_run_id,
            "commit_sha": workflow_sha,
        },
        "release": release,
        "artifacts": sorted_artifacts,
        "limitations": LIMITATIONS,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _artifact_from_inputs(
    *,
    platform: str,
    artifact_path: Path,
    source_path: Path,
    inspection_path: Path,
) -> dict[str, Any]:
    source = _load_json(source_path)
    inspection = _load_json(inspection_path)
    identity = file_identity(artifact_path)
    result = {
        "platform": platform,
        "filename": artifact_path.name,
        "sha256": identity["sha256"],
        "size": identity["size"],
        "source": source,
    }
    result.update(inspection)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Codex Desktop release manifest.")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--captured-at", default=_utc_now())
    parser.add_argument("--macos-artifact", type=Path)
    parser.add_argument("--macos-source", type=Path)
    parser.add_argument("--macos-inspection", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifacts = []
    if args.macos_artifact:
        artifacts.append(
            _artifact_from_inputs(
                platform="macos",
                artifact_path=args.macos_artifact,
                source_path=args.macos_source,
                inspection_path=args.macos_inspection,
            )
        )
    manifest = build_manifest(
        captured_at=args.captured_at,
        repository=args.repository,
        workflow_run_id=args.workflow_run_id,
        workflow_sha=args.workflow_sha,
        artifacts=artifacts,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
