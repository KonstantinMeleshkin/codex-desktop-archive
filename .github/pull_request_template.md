## Summary

-

## Verification

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `bash -n scripts/capture_source.sh`
- [ ] `bash -n scripts/inspect_macos.sh`
- [ ] `bash -n scripts/publish_release.sh`
- [ ] `bash -n scripts/verify_existing_release.sh`
- [ ] `python3 -m py_compile scripts/make_manifest.py scripts/render_release_notes.py scripts/should_release.py scripts/release_guard.py`

## Trust Impact

Describe whether this changes source URLs, verification rules, manifest fields, release immutability, or user-facing claims.
