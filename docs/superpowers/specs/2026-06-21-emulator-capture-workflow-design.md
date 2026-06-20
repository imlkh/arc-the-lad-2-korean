# Emulator Capture Workflow — Design

**Date:** 2026-06-21
**Status:** Approved (pending spec review)

## Problem

Static analysis cannot distinguish the remaining decoder-missed *dialogue* from
garbage: the text region holds real lines the template decoder never references,
interleaved with thousands of byte-runs that decode to plausible kana. Frequency,
grammar, and length heuristics all admit garbage (see
[[translation-coverage-checker]]). The only reliable oracle for "is this line
actually displayed?" is **runtime** — observe what the game draws.

## Goal

A repeatable workflow that, while the **patched** build is played in an emulator,
captures every displayed dialogue line, flags the ones still in Japanese (i.e.
missed by translation), and maps each to its STG file offset — producing a precise
worklist that feeds the existing translate → re-patch loop.

## Non-goals

- Automated/headless play. Coverage comes from a human playing (or a save-state
  tour); the workflow captures what is actually reached.
- Screen-pixel OCR. We hook the text handler, not the framebuffer.
- Translating inside the emulator. Capture only; translation uses the existing flow.

## Environment (verified)

- Emulator: **PCSX-Redux** (chosen for Lua + breakpoint/debugger API). Not yet
  installed; runbook covers install. DuckStation is present but lacks scripting.
- Disc image: `output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).cue`
  (+ `.bin`).
- Known address: dialogue **handler RAM = `0x80101560`** (from
  `python/patch/apply_hook.py`). This is the hook point.

## Approach: handler hook (chosen over RAM-watchpoint and display-buffer poller)

Hooking `0x80101560` yields both the displayed text AND its source pointer, so a
captured Japanese line maps directly to a translatable STG offset. The watchpoint
approach is noisy (reads ≠ displays); the display-buffer poller loses the
offset link.

**Division of labour (key design choice):** the Lua hook is *dumb* — it only reads
memory and logs raw `(ram_address, hex_bytes)`. All decoding, classification,
offset-mapping, and dedup happen in **Python**, reusing `decode_text`'s charmap
(tested) instead of reimplementing the encoding in Lua.

## Components

### 1. `tools/atl2_capture.lua`
PCSX-Redux Lua script. Sets an execution breakpoint at `0x80101560`. Two modes
(top-of-file flag):
- **`calibrate`** — on each of the first N hits, dump all GP registers and a
  64-byte memory window around each register value that looks like a RAM pointer
  (`0x80000000`–`0x801FFFFF`). The operator triggers one known line and identifies
  which register's window matches its bytes, and the RAM base of the loaded STG.
- **`capture`** — using the calibrated `TEXT_PTR_REG` and `RAM_BASE`, on each hit
  read the text pointer, read bytes until a `0x00` terminator (cap 256 B), and
  append `addr=0x........  bytes=XX XX ...` to `output/capture/capture.log`.
  In-session dedup by address to limit log size.

Constants at top: `MODE`, `HANDLER=0x80101560`, `TEXT_PTR_REG`, `RAM_BASE`,
`MAX_LEN=256`, `LOG_PATH`.

### 2. `python/tools/process_capture.py`
- Parse `capture.log` → list of `(ram_addr, bytes)`.
- Decode each via `decode_text.decode_string` + charmap.
- Classify: contains hiragana/katakana letters (U+3041–3096 / U+30A1–30FA, excl.
  U+30FC) → **still Japanese (missed)**; else already-Korean (skip).
- Map `ram_addr → STG file offset` using the calibrated `RAM_BASE` and chunk size
  (`file_offset = ram_addr - RAM_BASE + chunk_file_base`); the exact mapping is
  finalized once calibration gives `RAM_BASE`.
- Dedup by decoded text; emit `output/capture/missed_displayed.txt` in the
  `<id> / JP: / KO:` review format (KO blank, to be filled), plus coverage stats
  (total hits, unique lines, % still-Japanese).

### 3. `docs/emulator-capture.md` (runbook)
Steps: install PCSX-Redux → load the `.cue` → run `calibrate` mode → trigger the
treasure-chest line and identify `TEXT_PTR_REG` + `RAM_BASE` → switch to `capture`
mode → play for coverage → run `process_capture.py` → review/translate the
worklist → re-patch. Includes the known treasure-chest bytes
(`05 2A 1A 10 06 27 3E 0A 39`) as the calibration fingerprint.

## Data flow

```
play patched build → Lua breakpoint @0x80101560 → capture.log (addr, bytes)
  → process_capture.py (decode, classify, map offset, dedup)
  → output/capture/missed_displayed.txt  → translate (existing flow) → re-patch
```

## Calibration (the one runtime unknown)

Values that cannot be known statically and require one inspection run:
1. `TEXT_PTR_REG` — which register at `0x80101560` holds the text pointer.
2. `RAM_BASE` — where the active STG chunk is loaded in RAM, AND which STG/chunk it
   is (the loaded scene identity), since `addr → file offset` needs both the RAM
   base and the chunk's file base. The capture log will note the active scene
   (operator records which map they're in) so Python can pick the right chunk base;
   if scene identity proves hard to track, Python can instead match captured bytes
   against all stages' decoded text to recover the offset.

The `calibrate` mode surfaces both from a single known line (treasure chest). Until
calibrated, `capture` mode and the offset-mapping in `process_capture.py` are
parameterized by placeholders to be filled from the calibration result.

## Error handling

- Lua: if a register value is not in RAM range, skip it (no read). Cap string read
  at `MAX_LEN`. Never write outside `output/capture/`.
- Python: missing/empty `capture.log` → clear message, exit non-zero. Unmappable
  addresses → reported in a separate "unmapped" section, not silently dropped.

## Testing

- `process_capture.py` unit tests: feed a synthetic `capture.log` containing the
  treasure-chest bytes + one Korean line; assert it decodes both, classifies the
  chest as still-Japanese, maps its offset, and excludes the Korean one.
- Manual end-to-end: capture one known scene; confirm logged bytes match the
  expected message.

## Open questions

`TEXT_PTR_REG` and `RAM_BASE` are intentionally deferred to the calibration run —
they are runtime facts, not design gaps. Everything else is fully specified.
