#!/usr/bin/env python3
"""Decide whether a candidate Codex Desktop manifest deserves a new release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _artifact_key(artifact: dict[str, Any]) -> str:
    platform = artifact.get("platform", "unknown")
    classification = artifact.get("classification", "unknown")
    return f"{platform}:{classification}"


def _artifacts_by_key(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {_artifact_key(artifact): artifact for artifact in manifest.get("artifacts", [])}


def decide_release(
    latest: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    release = candidate.get("release", {})
    tag = release.get("tag")

    if latest is None:
        return {
            "should_release": True,
            "tag": tag,
            "reason": "no previous manifest",
        }

    reasons = []
    latest_release = latest.get("release", {})
    latest_identity = latest_release.get("identity", {})
    candidate_identity = release.get("identity", {})

    if latest_identity.get("version") != candidate_identity.get("version"):
        reasons.append("app version changed")
    if latest_identity.get("build") != candidate_identity.get("build"):
        reasons.append("app build changed")

    latest_artifacts = _artifacts_by_key(latest)
    candidate_artifacts = _artifacts_by_key(candidate)
    for key, candidate_artifact in candidate_artifacts.items():
        latest_artifact = latest_artifacts.get(key)
        platform = candidate_artifact.get("platform", "unknown")
        if latest_artifact is None:
            reasons.append(f"{platform} artifact added")
            continue
        if latest_artifact.get("sha256") != candidate_artifact.get("sha256"):
            reasons.append(f"{platform} sha256 changed")
        elif latest_artifact.get("size") != candidate_artifact.get("size"):
            reasons.append(f"{platform} size changed")

    for key in sorted(set(latest_artifacts) - set(candidate_artifacts)):
        platform = latest_artifacts[key].get("platform", "unknown")
        reasons.append(f"{platform} artifact removed")

    if reasons:
        return {
            "should_release": True,
            "tag": tag,
            "reason": ", ".join(reasons),
        }

    return {
        "should_release": False,
        "tag": tag,
        "reason": "all artifact identities unchanged",
    }


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide whether to publish a release.")
    parser.add_argument("--latest", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    latest = _load_optional_json(args.latest)
    with args.candidate.open("r", encoding="utf-8") as handle:
        candidate = json.load(handle)

    decision = decide_release(latest, candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(decision, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
