# Korean Patch Distribution (xdelta Release) — Design

**Date:** 2026-07-04
**Status:** Approved (Approach A: patch file + standard tools)

## Problem

The project currently produces a full 739 MB patched disc image
(`Arc the Lad II (Korean Patch).bin`). Distributing that file is both
legally risky (it contains the complete copyrighted game) and impractical
(size). We need to release something small that converts a user's own
original dump into the Korean version.

## Decision

Release a **16 MB xdelta (VCDIFF) patch file** plus the `.cue` and a
bilingual README as GitHub release assets. Users apply the patch with
existing, well-known tools — no custom patcher app or hosted web page.

Rejected alternatives:

- **Self-hosted web patcher (RomPatcher.js on GitHub Pages)** — nicer UX
  but adds a page to maintain; 739 MB in browser memory is sluggish.
  Can be added later without changing this design.
- **Custom standalone patcher executable** — per-OS builds plus unsigned
  binary warnings (SmartScreen/Gatekeeper) make it worse for users than
  a known community tool.

## Verified facts (2026-07-04)

- Source BIN (`output/patched/Arc the Lad II (Japan).bin.backup_20260206_001549.bin`)
  is a byte-exact redump dump of **"Arc the Lad II (Japan) (Rev 1)"**
  (PlayStation the Best, SCPS-91071/91310):
  size 739,144,224 bytes, MD5 `012B023097777CB6CE6A5DE5E0457022`,
  SHA-1 `EF170132080A3EE0AD5DA81028463D137BF4ABC0`, CRC32 `5BA1A361`.
- The original v1.0 release (SCPS-10026, MD5 `5AA6F83D2C2B3BE7EB14C2C9FBF2A9E3`)
  is a **different image**; the patch will not apply to it. A v1.0 patch
  cannot be built without a v1.0 dump — out of scope for now.
- `xdelta3 -e -9 -S lzma` produces a 16 MB patch in ~7 s; applying it to
  the Rev 1 original reproduces the Korean BIN byte-for-byte
  (round-trip MD5 verified).
- The patch is fully in-place: patched BIN size equals the original.

## Component

One new script: **`python/patch/make_release_patch.py`**, run as the
final step after `patch_workflow.py`. Steps:

1. **Verify source.** MD5 the original BIN; hard-fail unless it equals
   the redump Rev 1 hash above. A patch is never built from a modified
   source.
2. **Build.** `xdelta3 -e -9 -S lzma -s <original> <korean-bin> <patch>`.
   Output name carries the git version (`git describe --tags`), e.g.
   `arc-the-lad-2-korean-v0.1.0-beta.xdelta`.
3. **Verify result.** Apply the patch to the original into a temp file;
   require its MD5 to equal the Korean BIN's MD5; delete the temp file.
   Fail loudly on mismatch.
4. **Package.** Write a release folder `output/release/<version>/`
   containing:
   - `arc-the-lad-2-korean-<version>.xdelta`
   - `Arc the Lad II (Korean Patch).cue` (plain-text, freely distributable)
   - `SHA256SUMS.txt` (patch + cue)
   - `README.txt` — Korean first, English second: required dump
     ("Arc the Lad II (Japan) (Rev 1)", exact size and MD5), how to apply
     with Delta Patcher (Windows/macOS/Linux GUI) and with RomPatcher.js
     in the browser (no install), and a note that v1.0 dumps are not
     supported.

### CLI

```
python python/patch/make_release_patch.py \
    [--original PATH] [--patched PATH] [--out DIR]
```

All arguments default to the known project paths. The script requires
`xdelta3` on PATH (documented in README; `brew install xdelta` /
`apt install xdelta3`).

## Error handling

- Missing `xdelta3` → clear message with install hint, exit non-zero.
- Source MD5 mismatch → print expected vs. actual, name the redump title
  it should match, exit non-zero.
- Round-trip MD5 mismatch → delete outputs, exit non-zero (never ship an
  unverified patch).

## Testing

The script is self-testing: step 1 pins the input and step 3 proves the
output. A successful run *is* the correctness proof. Manual release
check: apply the shipped `.xdelta` with Delta Patcher or RomPatcher.js
once per release and boot in an emulator.

## Out of scope

- v1.0 (SCPS-10026) patch — needs a v1.0 dump.
- Hosted web patcher page — possible follow-up, independent of this.
- `--release` flag on `patch_workflow.py` — may be added later; the
  standalone script is the deliverable.
