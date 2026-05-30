# Security Policy

## Supported Scope

Security reports should focus on this repository's archival workflow, scripts, manifests, and release publication process.

Examples:

- workflow can publish unverified artifacts
- manifest can be forged or generated incorrectly
- release assets can be overwritten silently
- verification docs are dangerously wrong
- scripts trust unpinned or unexpected sources

## Not In Scope

- Vulnerabilities in Codex Desktop itself
- Vulnerabilities in OpenAI's download infrastructure
- Requests for official OpenAI support

## Reporting

Please open a GitHub issue if the report can be public.

If the report involves a sensitive exploit path, avoid posting exploit details publicly. Open a minimal issue saying that a private security report is needed, and the maintainer will coordinate a private channel.

## Security Principles

- No silent release overwrites.
- No custom repackaging of Codex Desktop installers.
- No stronger claims than stored evidence supports.
- macOS releases must pass signature and notarization checks before publication.
- macOS DMGs must not contain unexpected top-level entries or executable/package/script payloads outside `Codex.app`.
