# Verification Guide

This guide explains how to verify a release from this archive.

## Files To Download

From a GitHub Release, download:

- the macOS DMG
- `codex-desktop-manifest.json`

The manifest is the source of truth for the expected hash, size, source URL, workflow run, and verification results.

## macOS

### 1. Compare SHA-256

```bash
shasum -a 256 Codex-Desktop-*-macos.dmg
```

Compare the output with:

```json
artifacts[].sha256
```

for the artifact where:

```json
"platform": "macos"
```

### 2. Verify The DMG

```bash
hdiutil verify Codex-Desktop-*-macos.dmg
```

### 3. Mount Read-Only

```bash
hdiutil attach -readonly -nobrowse Codex-Desktop-*-macos.dmg
```

The mounted volume name may vary. Use `hdiutil info` if needed.

The workflow records the mounted DMG top-level inventory in the manifest and rejects unexpected top-level entries or executable/package/script payloads outside `Codex.app`.

### 4. Verify The App Signature

```bash
codesign --verify --verbose=4 "/Volumes/Codex Installer/Codex.app"
codesign -dv --verbose=4 "/Volumes/Codex Installer/Codex.app"
```

The signing identity should include:

```text
Developer ID Application: OpenAI OpCo, LLC (2DC432GLL2)
```

### 5. Verify Gatekeeper Assessment

```bash
spctl -a -vv -t exec "/Volumes/Codex Installer/Codex.app"
```

### 6. Verify Notarization Ticket

```bash
xcrun stapler validate "/Volumes/Codex Installer/Codex.app"
```

### 7. Detach The Volume

```bash
hdiutil detach "/Volumes/Codex Installer"
```

## Evidence Levels

`strong` means:

- the artifact hash and size were recorded
- the source URL metadata was recorded
- macOS signature checks passed
- macOS notarization checks passed
- OpenAI Team ID matched `2DC432GLL2`
- mounted DMG inventory had no unexpected top-level entries or external executable/package/script payloads

`partial` means:

- the artifact hash and source metadata were recorded
- at least one stronger app-level verification step was unavailable
