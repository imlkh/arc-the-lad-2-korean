# Arc the Lad 2 Korean Patching Guide

## Overview

The Korean translation patch replaces Japanese text with Korean in STG dialogue files and system messages.

**IMPORTANT:** Use `patch_all.py` to patch multiple files together. See [Critical Issue](#critical-issue-separate-patching) below.

## Quick Start (Recommended)

Use the workflow orchestrator to run all patching steps automatically:

```bash
# Run complete workflow (S100 + SG00 by default)
python python/patch/patch_workflow.py

# Patch specific stages
python python/patch/patch_workflow.py S100 SG00 S200

# Patch all available stages
python python/patch/patch_workflow.py --all

# Validation only (no patching)
python python/patch/patch_workflow.py --validate-only
```

The workflow performs:
0. **Validation** - Check for truncation issues and `[box:speech][delay:00]` in wrong regions
1. **Copy translations** - Copy `translated/ko/*.txt` to `output/patched/translation/`
2. **Font + fixed-length patching** - Unified character mapping
3. **Variable-length patching** - VLUT for each stage
4. **Hook application** - Multi-chunk hook to SCPS_100.26
5. **Disc image patching** - Apply all patches to BIN file

Output: `output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin`

## Critical Issue: Separate Patching

### The Problem

When patching files separately with `patch_korean.py`:

```bash
python python/patch_korean.py S100    # Creates font with 627 chars
python python/patch_korean.py SG00    # OVERWRITES font with 668 chars
python python/patch_korean.py --system # OVERWRITES font with 53 chars!
```

Each run **overwrites COMM.IMG** with only the characters needed for that file.

**Result:** Characters unique to earlier files are lost:
- S100 has 96 chars not in SG00
- SG00 has 137 chars not in S100
- Running `--system` last leaves only 53 chars in the font!

### The Solution: `patch_all.py`

The combined patcher:
1. Extracts ALL Korean characters from ALL translation files (764 total)
2. Creates ONE unified font mapping in COMM.IMG
3. Patches all STG files using the same mapping

```bash
python python/patch_all.py
```

### Character Distribution

| File | Description | Entries |
|------|-------------|---------|
| S100_STG.txt | Stage dialogue | 1,309 |
| SG00_STG.txt | Stage dialogue | 2,391 |
| SCPS_100_26.txt | System, char names (2 tables) | 1,732 |
| SDIC_BIN.txt | Monster descriptions | 220 |
| YGUILD_BIN.txt | Guild quests | 352 |
| SMITH_BIN.txt | Equipment effects | 598 |
| BEAM_DAT.txt | Battle text, char names (2 tables) | 2,831 |
| **Unified Font** | Total Korean glyphs | **1,014** |

## Patching Modes

### Fixed-length Mode (Default)

**How it works:**
- Replaces Japanese text with Korean at the exact same offset
- Korean text is truncated if it exceeds the original byte length
- No structural changes to the file

**Pros:**
- Safe - cannot corrupt file structure
- Works with any file type (STG, EXE, etc.)

**Cons:**
- Long Korean translations get cut off
- Typically 5-20% of dialogues are truncated

### Reflow Mode (`--reflow`) - EXPERIMENTAL

**Status:** Not working correctly. Causes game to skip dialogues or jump to wrong scenes.

**How it was supposed to work:**
1. Parse the entire text region (offset 0xB4000-0xBC7FF in each chunk)
2. Rebuild the region with new Korean text (variable length)
3. Recalculate all script prefix offsets
4. Update template pointers (Ptr_A at +14, Ptr_B at +30)

**Issues found:**
- Template pointer recalculation may be incorrect
- Game code has hardcoded references that don't get updated
- Causes unpredictable behavior (battle screens instead of dialogues)

**Recommendation:** Use fixed-length mode until reflow is properly debugged.

### Why Alternative Approaches Don't Work

Multiple approaches were investigated to enable variable-length translations. All have been proven infeasible:

| Approach | Status | Reason |
|----------|--------|--------|
| MIPS patching | NOT FEASIBLE | No direct address references to text region |
| Script prefix redirection | NOT FEASIBLE | Prefix is metadata, not a lookup key |
| Text relocation | NOT FEASIBLE | Event script uses sequential streams |
| Reflow mode | BROKEN | Template pointer updates cause crashes |

**Key Finding**: The game uses a **stream-based sequential reading model**:
- Dialogues are organized in streams (ref_ids: A9, AA, AB, 66)
- The `0x0067` event command reads the NEXT dialogue from the specified stream
- Text is embedded inline, not accessed via pointer lookup
- There is no mechanism to redirect to arbitrary memory locations

The script prefix (e.g., `16 07`) is metadata, not a lookup key. The same prefix appears with different text at different locations.

**Update (2026-02-06)**: Variable-length patching is now possible via interpreter hook. See below.

For complete technical details, see `DIALOGUE_SYSTEM_ANALYSIS.md`.

### Variable-Length Mode - WORKING

**Status**: Multi-chunk variable-length patching tested and working (2026-02-06).

A new approach using interpreter hooking enables variable-length translations:

1. Hook the text advance handler via jump table redirection
2. Store per-chunk VLUT (Variable Length Lookup Table) in padding region
3. Master pointer at 0xAFF00 tells trampoline where to find each chunk's VLUT
4. Korean text written to padding region after VLUT
5. Template-driven dialogue extraction using `decode_text.py:scan_stg()`

**Workflow** (use `patch_workflow.py` instead for automated execution):
```bash
# 1. Standard Korean patching (font + fixed-length text)
python python/patch/patch_all.py

# 2. Apply variable-length patching with per-chunk VLUTs
python python/patch/patch_variable_length_multi.py S100
python python/patch/patch_variable_length_multi.py SG00
python python/patch/patch_variable_length_multi.py S200

# 3. Apply multi-chunk hook to SCPS_100.26
python python/patch/apply_hook.py --variable-length-multi

# 4. Apply to disc image
python python/patch/patch_bin.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
```

**S100.STG Results** (11 chunks):
- 1,207 dialogues patched with variable-length VLUT
- 98 dialogues use fixed-length fallback
- Chunk 8 has no padding space (fixed-length only)

**SG00.STG Results** (56 chunks):
- 1,152 dialogues patched with variable-length VLUT
- 1,244 dialogues use fixed-length fallback
- 15 chunks have no padding space: 0, 4, 5, 6, 8, 9, 10, 11, 22, 24, 31, 39, 40, 46, 53

**S200.STG Results** (17 chunks, verified 2026-02-08):
- 1,104 dialogues patched with variable-length VLUT
- 936 dialogues use fixed-length fallback
- 7 chunks have no padding space: 0, 5, 9, 10, 14, 15, 16

For implementation details, see `VARIABLE_LENGTH_IMPLEMENTATION.md`.

## Handling Truncated Dialogues

With fixed-length mode, some dialogues will be truncated. Options:

### Option 1: Shorten Translation
Rephrase to use fewer characters:
```
Original: 하지만, 로말리아를 우습게 보면 곤란해
Shortened: 하지만 로말리아를 얕보면 곤란해
```

### Option 2: Use `[cursor]` Tag (NOT recommended for truncation)

**WARNING:** The `[cursor]` tag (FF 08 07 01) adds 4 bytes to the text, making it LONGER not shorter. It does NOT help with truncation.

The `[cursor]` tag is only useful when:
- The original Japanese text already uses page breaks
- You have spare space and want dramatic pauses

```
# This INCREASES byte count by 4 - does NOT solve truncation!
물은 낮은 곳으로 흐르고,[cursor]사람은 쉬운 곳으로 흐르지
```

### Finding Truncated Dialogues
```bash
python python/find_truncated.py S100 --output output/truncated_S100.txt
```

## File Structure Reference

### STG Chunk Layout (772,096 bytes)
| Offset | Size | Content |
|--------|------|---------|
| 0x00000 | 0x70000 | Graphics |
| 0x77000 | 0x09000 | MIPS code (scene-specific) |
| 0x80000 | 0x20000 | MIPS code (main logic) |
| 0xB4000 | 0x08800 | Text region (dialogues + templates) |

### Dialogue Format
```
[2-byte script prefix][encoded text][00 null terminator]
```

### Template Structure (48 bytes)
- Bytes 0-3: Signature `0x8BF00123`
- Bytes 4-5: Speaker opcode
- Bytes 14-15: Ptr_A (`script_prefix + 0x10`)
- Bytes 16-19: Signature `0x8BF00145`
- Bytes 30-31: Ptr_B (`Ptr_A + 0x05`)

### Dialogue Types

The decoder captures five types of dialogues:

| Type | Region | Context Opcode | Detection |
|------|--------|----------------|-----------|
| Template-associated | 0xB4000-0xBC7FF | 0xFFFE/0x80XX | 48-byte template block |
| Orphan menus | 0xB4000-0xBC7FF | 0x00A9 | `[br][opt]` pattern |
| Bare dialogues | 0xB4000-0xBC7FF | 0x00B4 | A9 00 + kanji (no template/opt) |
| Event Script | 0xB0000-0xB4000 | 0x00B0 | A9 00 + strict validation |
| Padding | 0xA0000-0xB0000 | 0x00A0 | A9 00 + strict validation |

**Bare dialogues** are A9 00 texts without templates or [opt] tags:
- Location names (コルボ平原, ラウス平野)
- Battle messages (戦闘に参加するキャラクターを選んで下さい)
- Scene announcements (持ち場につけ！)

**Strict validation** requires: `[box:]` tag OR kanji OR `[br][opt]` pattern.

```bash
# Regenerate decoded output with all dialogue types
python python/decode/decode_text.py /path/to/S100.STG --stg > output/decoded/stg/S100_STG.txt
```

S100.STG dialogue breakdown:
- 1,165 template-associated dialogues
- 39 bare dialogues (location names, battle messages, bounty cards)
- 75 orphan menus (filtered from 97 using `[br][opt]` pattern)
- 33 Event Script region dialogues
- 7 Padding region dialogues
- **Total: 1,319 dialogues**

SG00.STG dialogue breakdown:
- 1,495 template-associated dialogues
- 365 bare dialogues
- 401 orphan menus
- 143 Event Script region dialogues
- 25 Padding region dialogues
- **Total: 2,429 dialogues**

### Character Encoding

Korean characters are mapped to font cell IDs:
- CharIDs 1-159, 187-212: Single-byte encoding (185 slots, most frequent chars)
- CharIDs 239+: Two-byte encoding (F0 XX, F1 XX, etc.)
- Packed list characters (with `[FF:1A]` separators) are prioritized for single-byte slots to avoid byte overflow

**Avoided IDs:** 239, 494, 749, 1004, 1259, 1514 encode with 0x00 byte (null terminator conflict)

### Packed Item List Encoding

SCPS_100.26 and BEAM.DAT contain packed item lists — multiple item names stored in a single null-terminated string, separated by FF control codes.

| File | Separator | Item Prefix (original) | Encoding Function |
|------|-----------|----------------------|-------------------|
| SCPS_100.26 | `FF 1A 00 00` | `FF 1B/1C/1D XX YY` (text compression) | `encode_packed_list()` |
| BEAM.DAT | `FF 19 00 00` | `FF 1A XX YY` (text compression) | `encode_korean_text()` |

**Important**: All FF control codes are 4 bytes (`FF + opcode + param1 + param2`). Separators must always be written as exactly 4 bytes. Writing fewer bytes causes the game to consume the first byte(s) of the next item as separator parameters, resulting in item misalignment.

The original game uses FF prefix codes (`FF 16-1D XX YY`) as text compression macros that insert substrings (e.g., `[FF:16 5F E3]ド` expands to "ソード"). Korean translations replace these with full text, which the game renders correctly without prefix codes.

**SCPS packed lists** (36 entries, 0x0D44AE–0x0D4CB0): Detected by `[FF:1A` in translation text, encoded via `encode_packed_list()`.

**BEAM packed lists** (24+ entries, 0x0216E4CC–0x0216EB72): Use `[FF:19 00 00]` separators in translation text, encoded via the generic `encode_korean_text()` which handles `[FF:XX YY ZZ]` tags as 4-byte codes.

## Output Files

After patching:
```
output/patched/
├── Arc the Lad II (Japan)/
│   └── Arc the Lad II (Japan).bin   # Patched disc image
├── translation/                      # Translations used for patching
│   ├── S100_STG.txt
│   ├── SG00_STG.txt
│   ├── SCPS_100_26.txt
│   ├── SDIC_BIN.txt
│   └── YGUILD_BIN.txt
├── COMM.IMG                          # Patched font (895 Korean glyphs)
├── S100.STG                          # Patched stage file
├── SG00.STG                          # Patched stage file
├── SCPS_100.26                       # Patched executable
├── SDIC.BIN                          # Patched dictionary
├── YGUILD.BIN                        # Patched guild data
└── unified_charmap.txt               # Character mapping reference
```

The `translation/` subdirectory preserves the exact translation files used for patching, ensuring traceability.

## Current Status

### Patched Files

| File | Mode | Entries | Notes |
|------|------|---------|-------|
| COMM.IMG | font | ~1,014 glyphs | Unified Korean font |
| S100.STG | variable | 1,309 (fixed) + 1,204 (VLUT) | 10/11 chunks with VLUT |
| SG00.STG | variable | 2,391 (fixed) + 1,149 (VLUT) | 41/56 chunks with VLUT |
| S200.STG | variable | 1,872 (fixed) + 1,104 (VLUT) | 10/17 chunks with VLUT |
| SCPS_100.26 | fixed | 1,645 | System text, monsters, skills, locations + hook |
| SDIC.BIN | fixed | 218 | Character profiles, monster descriptions |
| YGUILD.BIN | fixed | 351 | Guild quest descriptions |

### Not Yet Translated

| File | Strings | Menu Options | Description | Priority |
|------|---------|--------------|-------------|----------|
| **BEAM.DAT** | 2,753 | 686 | Battle/event dialogues | High |
| **SMITH.BIN** | 568 | 15 | Equipment/smithing effects | Medium |
| **YSHOP.BIN** | 1 | 0 | Shop/item text | Low |
| **YPROP.BIN** | 5 | 0 | Item descriptions | Low |
| **YSEG.BIN** | 2 | 0 | Character text | Low |
| **YEND.BIN** | 155 | 0 | ASCII credits (English names) | N/A |
| **CHA.BIN** | 0 | 0 | Character data | N/A |

**Menu option examples by file:**

- **BEAM.DAT**: System prompts (exit?, yes/no), navigation (ladder, warp zone, switch)
- **YGUILD.BIN**: Complete guild quest descriptions with success/failure text
- **SMITH.BIN**: Equipment effect descriptions (avoid abnormality, additional attack)

### Decoding Non-STG Files

```bash
# Decode all binary files
python python/decode/decode_all_bin.py

# Decode YEND.BIN credits (ASCII)
python python/decode/decode_yend.py

# Output location
output/decoded/bin/*.txt
```

## Troubleshooting

### Garbled/Wrong Characters
- **Cause:** Font mapping mismatch between COMM.IMG and STG files
- **Solution:** Use `patch_all.py` to ensure unified mapping

### Game Skips Dialogues or Crashes
- **Cause:** Reflow mode corrupted template pointers
- **Solution:** Use fixed-length mode (default)

### Some Korean Text Cut Off
- **Cause:** Korean translation longer than original Japanese
- **Solution:** Shorten translation or use `[cursor]` splits

### Dialogue Box Too Wide
- **Cause:** Korean lines longer than Japanese without proper line breaks
- **Status:** Known issue - TO BE FIXED
- **Note:** The `[br]` tags in translation files are currently NOT encoded (skipped)
- **Attempted fix:** Encoding `[br]` → `FF 05 01 01` caused game crashes
- **Root cause investigation needed:** See MEMORY.md for details

### Game Freezes on Bounty Board / Specific Scenes
- **Cause:** Decoder false positive — event script opcodes in the text region
  were misidentified as bare dialogue entries. Patching these offsets overwrites
  store opcodes (`23 01 XX 8C`) with Korean character bytes, corrupting
  the game's script execution.
- **Example:** `0x001780CC` in S100.STG chunk 1 — the `A9 00` at `0x1780CA`
  is a script command, not a text entry marker. The bytes after it decode to
  garbage: `もあがデわしもあをデタギもあんデ喚J`.
- **Solution:** Garbage filter Rule 6 in `_is_garbage_text()` detects repeating
  2-character pairs at regular intervals (≥4 chars apart, ≥3 occurrences),
  which is the fingerprint of repeated opcodes decoded as text.
- **If it recurs:** Check the decoded text — garbage with repeating character
  patterns indicates opcode data. Remove the entry from the translation file.

### Pure Kana Dialogue Missing from Decoded Output
- **Cause:** Event script (0x00B0) and padding (0x00A0) scanners use strict
  validation requiring `has_box_tag or has_kanji or is_menu`. Pure kana
  dialogue like `やめろ！！` or `なにもはいっていないようだ` fails all checks.
- **Solution (2026-02-08):** Two-pronged approach:
  1. **Stronger garbage filter (Rule 7):** Detects MIPS opcode garbage by checking
     for 2+ distinct characters preceding `あ`/`ぁ`, `デ`, or `ギ` — the signature
     of VM opcodes (XX 01, XX 8C, XX 80) decoded as text.
  2. **Additional acceptance criteria:**
     - `is_pure_kana`: kana text with punctuation (`！？…。`)
     - `is_long_hiragana`: pure hiragana text ≥13 characters
- **Action required:** Regenerate decoded output and check for new entries with
  `[0x00A0]` or `[0x00B0]` context opcodes.

### Menu Options Not Translated
- **Cause:** Orphan menu texts (without templates) were not captured by the decoder
- **Solution:** Updated decoder now captures orphan menu texts (2026-02-06)
- **Action required:**
  1. Regenerate decoded output: `python python/decode/decode_text.py <STG_FILE> --stg`
  2. Look for lines with `[0x00A9]` context opcode (orphan menus)
  3. Add translations to translation file
  4. Re-run patcher
