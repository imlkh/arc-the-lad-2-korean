# Arc the Lad 2 Korean Patching Guide

## Overview

The Korean translation patch replaces Japanese text with Korean in STG dialogue files and system messages.

**IMPORTANT:** Use `patch_all.py` to patch multiple files together. See [Critical Issue](#critical-issue-separate-patching) below.

## Quick Start (Recommended)

```bash
# Patch all files with unified character mapping
python python/patch_all.py

# Apply to disc image
python python/patch_bin.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
```

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

| File | Unique Chars | Shared | Total |
|------|--------------|--------|-------|
| S100_STG.txt | 96 | 531 | 627 |
| SG00_STG.txt | 137 | 531 | 668 |
| SCPS_100_26_system.txt | 0 | 53 | 53 |
| **Combined** | - | - | **764** |

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

**Workflow**:
```bash
# 1. Standard Korean patching (font + fixed-length text)
python python/patch_all.py

# 2. Apply variable-length patching with per-chunk VLUTs
python python/patch_variable_length_multi.py S100
python python/patch_variable_length_multi.py SG00

# 3. Apply multi-chunk hook to SCPS_100.26
python python/apply_hook.py --variable-length-multi

# 4. Apply to disc image
python python/patch_bin.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
```

**S100.STG Results** (11 chunks):
- 1,053 dialogues patched with full-length Korean translations
- 92 dialogues skipped (no translation or no space)
- Chunk 8 uses fixed-length fallback (no padding space)

**SG00.STG Results** (56 chunks):
- 685 dialogues patched with full-length Korean translations
- 785 dialogues skipped (15 chunks have no padding space)
- Chunks without space: 0, 4, 5, 6, 8, 9, 10, 11, 22, 24, 31, 39, 40, 46, 53

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
- 40 bare dialogues (location names, battle messages)
- 76 orphan menus (filtered from 97 using `[br][opt]` pattern)
- 33 Event Script region dialogues
- 7 Padding region dialogues
- **Total: 1,321 dialogues**

SG00.STG dialogue breakdown:
- 1,495 template-associated dialogues
- 377 bare dialogues
- 403 orphan menus
- 144 Event Script region dialogues
- 26 Padding region dialogues
- **Total: 2,445 dialogues**

### Character Encoding

Korean characters are mapped to font cell IDs:
- CharIDs 1-159: Single-byte encoding (most frequent chars)
- CharIDs 239+: Two-byte encoding (F0 XX, F1 XX, etc.)

**Avoided IDs:** 239, 494, 749, 1004, 1259, 1514 encode with 0x00 byte (null terminator conflict)

## Output Files

After patching:
```
output/patched/
├── Arc the Lad II (Japan)/
│   └── Arc the Lad II (Japan).bin   # Patched disc image
├── COMM.IMG                          # Patched font (764 Korean glyphs)
├── S100.STG                          # Patched stage file
├── SG00.STG                          # Patched stage file
├── SCPS_100.26                       # Patched executable
└── unified_charmap.txt               # Character mapping reference
```

## Current Status

### STG Files (Variable-Length Patching)

| File | Mode | Total Dialogues | Patched | Notes |
|------|------|-----------------|---------|-------|
| COMM.IMG | - | - | 854 glyphs | Unified Korean font |
| S100.STG | variable | 1,321 | 1,053 | 10/11 chunks with VLUT |
| SG00.STG | variable | 2,445 | 685 | 41/56 chunks with VLUT |
| SCPS_100.26 | fixed | 250+ | 250 | System text, location names + hook |

### Non-STG Files (Not Yet Translated)

These binary files contain translatable text but do not have translation files yet:

| File | Strings | Menu Options | Description | Priority |
|------|---------|--------------|-------------|----------|
| **BEAM.DAT** | 2,753 | 686 | Battle/event dialogues | High |
| **YGUILD.BIN** | 352 | 109 | Guild quest descriptions | Medium |
| **SMITH.BIN** | 598 | 15 | Equipment/smithing effects | Medium |
| **SDIC.BIN** | 220 | 0 | Character profiles, monster descriptions | Low |
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

### Menu Options Not Translated
- **Cause:** Orphan menu texts (without templates) were not captured by the decoder
- **Solution:** Updated decoder now captures orphan menu texts (2026-02-06)
- **Action required:**
  1. Regenerate decoded output: `python python/decode/decode_text.py <STG_FILE> --stg`
  2. Look for lines with `[0x00A9]` context opcode (orphan menus)
  3. Add translations to translation file
  4. Re-run patcher
