# codex-desktop-archive

Unofficial, evidence-based archive of historical Codex Desktop installers.

This repository exists for one practical reason: if a new Codex Desktop update breaks your workflow, you should have a transparent way to return to a previous desktop build.

## What Is Archived

| Platform | Status | Evidence level |
| --- | --- | --- |
| macOS | Full DMG from the official OpenAI-linked download URL | Strong |

This project does not archive Codex CLI. Codex CLI has its own open-source release channel.

## Official Source URLs

The workflow captures the platform download URLs linked from the Codex page:

- Codex page: <https://openai.com/codex/>
- macOS: <https://persistent.oaistatic.com/codex-app-prod/Codex.dmg>

## Trust Model

Every release is based on a manifest. The manifest records:

- source URL and effective URL observed by the downloader
- selected HTTP headers
- SHA-256 and byte size
- GitHub Actions run id
- workflow commit SHA
- app version/build when inspectable
- mounted DMG inventory
- platform-specific verification results
- known limitations

For macOS, the workflow verifies the DMG and checks that the app is signed and notarized as:

```text
Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)
```

## Release Policy

The capture workflow runs once per day at `06:17 UTC` and can also be started manually with `workflow_dispatch`.

The workflow creates a new release only when the captured artifact identity changes.

It skips release creation when the current capture has the same app version/build and artifact hashes as the latest manifest.

Existing release assets are not silently overwritten. The workflow does not use `gh release upload --clobber`.

Publication is separated from capture and read-only verification. The final publish job is the only job with `contents: write`, and it re-inspects the macOS DMG before publishing.

Skipped captures still verify the already-published GitHub Release against `manifest/latest.json`, including asset hashes, attached manifest, release notes, and tag target.

## Verify A macOS Release

Download the DMG and `codex-desktop-manifest.json` from the same GitHub Release, then compare the hash:

```bash
shasum -a 256 Codex-Desktop-*-macos.dmg
```

The output should match the `sha256` field for the macOS artifact in the manifest.

Then verify the disk image and app signature:

```bash
hdiutil verify Codex-Desktop-*-macos.dmg
hdiutil attach -readonly -nobrowse Codex-Desktop-*-macos.dmg
codesign --verify --verbose=4 "/Volumes/Codex Installer/Codex.app"
spctl -a -vv -t exec "/Volumes/Codex Installer/Codex.app"
xcrun stapler validate "/Volumes/Codex Installer/Codex.app"
hdiutil detach "/Volumes/Codex Installer"
```

See [docs/verification.md](docs/verification.md) for the full verification guide.

## Windows

Windows is intentionally not supported by this archive. The current official Windows download path uses a Store bootstrapper, which can install whatever version Microsoft Store resolves at install time. That does not provide the same historical rollback guarantee as archiving a complete macOS DMG.

## Limits

This project can prove what its workflow downloaded and published.

It cannot mathematically prove what OpenAI served on a historical date unless OpenAI or another independent source published the historical hash.

This project is not affiliated with OpenAI.
