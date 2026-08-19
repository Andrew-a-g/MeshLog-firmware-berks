# Release and validation policy

The repository distinguishes short-lived development artifacts from tagged releases. CI artifacts remain explicitly `UNVALIDATED` and must not be linked as supported downloads. A tagged release may be marked `VALIDATED` only after the project owner has explicitly confirmed physical operation of every included target and authorized publication.

## Roles and evidence

A release candidate needs:

- a named release owner;
- a second person reviewing source revision, dependency changes, manifest, and checksums;
- a tester and physical test record for every board included in the manifest;
- the exact Git commit, version, build epoch, artifact SHA-256, board revision, tester, date, and pass/fail result in the release notes or linked test record.

Compilation, unit tests, or a boot reported by somebody else are not substitutes for physical validation. Failed or untested boards must be rebuilt after removal from the package matrix, or the entire candidate must remain unpublished.

## Candidate procedure

1. Build BerksMesh candidates from the reviewed `berksmesh` branch, not `dev`; `berksmesh` carries the built-in `#berks`, `#berksbot`, and `#jokes` channels. Merge reviewed current changes into that branch deliberately, fetch `upstream/main`, and inspect both commit and path divergence. Never resolve `MyMesh.h` conflicts by taking an entire side.
2. Confirm the radio flags remain exactly 869.618 MHz, 62.5 kHz, SF8, CR 4/8. Review every dependency/platform version change.
3. Choose a commit-unique version and build once from a clean checkout using the commands in `README.md`. Use the commit timestamp as `SOURCE_DATE_EPOCH`. Confirm every per-environment provenance marker contains the exact full `HEAD`, epoch, and clean-tree assertion.
4. Run the unit tests, all six PlatformIO builds, packaging, and `sha256sum --check SHA256SUMS`. Confirm `SHA256SUMS` covers `manifest.json` and keep the complete logs. Use a new output path; candidate directories are immutable.
5. Rebuild independently from another clean checkout with the same OS image/tool versions and epoch. Compare every `.bin`, `manifest.json`, and `SHA256SUMS` byte-for-byte. These controls test repeatability under the stated conditions; they are not a general reproducibility guarantee. Investigate any mismatch; do not release it.
6. For **each** exact artifact checksum, use the documented merged-image process to flash its matching physical board. Record hardware revision and power/radio setup.
7. Perform at minimum:
   - erase, flash at `0x0`, boot, reboot, and power-cycle;
   - serial CLI access at 115200 baud and absence of reset loops;
   - configuration save/load across reboot;
   - Wi-Fi association and reconnect;
   - HTTPS logger submission and authentication behavior;
   - `channel ls` shows `Public`, `#berks`, `#berksbot`, and `#jokes` in slots 0–3; their embedded PSKs are public/shared interoperability values, while any private channel PSK must not be exposed in logs;
   - bidirectional packets with a known-good BerksMesh node using 869.618 MHz / 62.5 kHz / SF8 / CR 4/8;
   - a sustained run appropriate to the release risk, checking watchdog resets and message delivery.
8. Have the reviewer verify the physical evidence, manifest metadata, and checksums. Only after the project owner explicitly confirms every included target and authorizes publication may the owner create a `v*` tag. The guarded tag workflow rebuilds the exact tagged source, packages it as `VALIDATED`, checks every checksum, and publishes the immutable release assets.
9. Read back the published release, asset list, manifest and checksums. If any expected target or file is absent, remove the release and issue a corrected new version rather than replacing files in place.

## Release notes and downloads

Release notes must distinguish configured targets, successfully compiled targets, and physically validated/supported hardware. They must state:

- supported board revisions and exact filenames;
- radio profile and regional/legal caveat;
- source commit and upstream base;
- changes from the previous checked release;
- test scope, tester/date, known limitations, and upgrade/rollback steps;
- SHA-256 verification instructions;
- that only artifacts with recorded physical validation are supported.

Do not call ordinary workflow artifacts “releases,” “stable,” or “hardware tested,” and do not put them on a downloads page. Only immutable assets from a `VALIDATED` tagged release may be linked as supported downloads. No browser flasher should be added until board detection, erase/backup expectations, recovery, and physical tests have their own reviewed design.

## Rollback and incident response

Retain the previous checked bundle, checksums, source commit, and flashing instructions. If field behavior differs from validation:

1. remove or clearly mark affected downloads;
2. publish a concise advisory identifying checksums and boards;
3. direct users to the previous checked image and explain configuration erase/restore implications;
4. reproduce and fix on `dev`;
5. create a new candidate and repeat the complete validation procedure—never replace files under an existing version.

Support requests should begin with board/revision, manifest version, artifact SHA-256, flashing command, and sanitized serial logs. Never request private keys, channel PSKs, Wi-Fi passwords, or logger authentication secrets.

Release-matrix builds intentionally omit private-key export while retaining import for controlled recovery. Export-capable migration builds, if ever needed, must be separately reviewed and tightly handled; an exported private key enables node impersonation. Public channel keys embedded in this repository are interoperability values and should not be described as confidential, but that does not make other channel PSKs public.
