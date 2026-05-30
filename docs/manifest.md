# Manifest Format

Every release includes `codex-desktop-manifest.json`.

The manifest is designed to be readable by humans and strict enough for scripts.

## Top-Level Fields

```json
{
  "schema_version": "1.0",
  "captured_at": "2026-05-30T12:34:56Z",
  "source_page": "https://openai.com/codex/",
  "repository": "KonstantinMeleshkin/codex-desktop-archive",
  "workflow": {
    "run_id": "123456789",
    "commit_sha": "0123456789abcdef0123456789abcdef01234567"
  },
  "release": {
    "tag": "desktop-v26.527.31326",
    "title": "Codex Desktop 26.527.31326",
    "identity": {
      "product": "codex-desktop",
      "version": "26.527.31326",
      "build": "3390"
    },
    "evidence_level": "strong"
  },
  "artifacts": [],
  "limitations": []
}
```

## Artifact Fields

Each artifact records:

- platform
- classification
- filename
- SHA-256
- byte size
- source metadata
- app metadata when available
- mounted DMG top-level inventory and rejected external payload list
- verification result

## Classifications

`full-installer`:

- The artifact is a full installer package for a platform.
- Current macOS DMG captures use this classification.

## Release Identity

When the macOS app version is available, release tags use:

```text
desktop-v<version>
```

Example:

```text
desktop-v26.527.31326
```

When app version is not available, tags fall back to:

```text
desktop-capture-YYYY-MM-DD
```

Fallback manifests use `partial` evidence level. The publication workflow currently rejects partial manifests, so normal public releases require a macOS app version and strong evidence.
