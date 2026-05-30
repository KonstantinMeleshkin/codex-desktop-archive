# Maintainer Runbook

## Routine Operation

The scheduled workflow runs daily at `06:17 UTC`. It can also be run manually with `workflow_dispatch`.

Expected outcomes:

- New Codex Desktop version: workflow publishes a new release.
- Same Codex Desktop version: workflow skips release creation after verifying the existing GitHub Release still matches `manifest/latest.json`.
- Verification failure: workflow fails and publishes nothing.

## Manual Run

Use GitHub Actions:

1. Open the `Capture Codex Desktop` workflow.
2. Run `workflow_dispatch`.
3. Inspect the workflow summary.
4. If a release was created, verify the attached manifest and release notes.

## Before Publicizing The Repository

Check:

- README is current.
- `SECURITY.md` is present.
- The latest release has `codex-desktop-manifest.json`.
- The latest release notes include hashes and limitations.
- The workflow has not used `--clobber`.

## Failure Handling

If macOS signature or notarization fails:

- do not publish the artifact
- check whether the official source URL changed
- check whether GitHub Actions macOS tooling changed
- open an issue with the captured failure details

If a tag already exists with different bytes:

- do not overwrite it
- open an issue
- compare the existing release manifest with the candidate manifest
- publish a corrected release only with explicit maintainer review

## Local Test Commands

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/capture_source.sh
bash -n scripts/inspect_macos.sh
bash -n scripts/publish_release.sh
bash -n scripts/verify_existing_release.sh
python3 -m py_compile scripts/make_manifest.py scripts/render_release_notes.py scripts/should_release.py scripts/release_guard.py
```
