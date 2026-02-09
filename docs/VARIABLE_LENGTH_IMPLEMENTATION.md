# Variable-Length Translation Implementation Plan

## Summary

This document outlines the implementation path for enabling variable-length Korean translations in Arc the Lad 2.

## Current Status

**Phase 1-4 COMPLETE**: **ALL STG FILES SUPPORTED** (2026-02-09)

- Passthrough hook: Tested and working
- Lookup table hook: Tested and working (after branch offset fix)
- Chunk base calculation (`TextPtr & 0xFFF00000`): Confirmed correct
- **Multi-chunk variable-length**: **WORKING** (S100.STG, SG00.STG, S200.STG)
- **Auto-detection**: **WORKING** (remaining 16 STG files auto-detect free padding space)

**Fixed-length patching**: Working, but truncates ~5-20% of dialogues.

**Variable-length patching**: **WORKING** - Full-length Korean translations without truncation.

### Key Discoveries (2026-02-06)

**Branch Offset Bug Fix**: Initial VLUT lookup hook caused game freeze due to incorrect MIPS branch offsets. See "Branch Offset Debugging" section below.

**Per-Chunk VLUT Offsets**: Each chunk has different amounts of data in the "padding" region (0xA0000-0xB0000). VLUT must be placed at different offsets per chunk.

**Master Pointer Solution**: Store a "master pointer" at fixed offset 0xAFF00 that points to each chunk's VLUT location. The trampoline reads this pointer first.

**Template-Driven Dialogue Extraction**: Using `decode_text.py:scan_stg()` for proper dialogue detection instead of simple A9 00 marker scanning. The scanner now captures five dialogue types: template-associated, bare dialogues, orphan menus, event script, and padding region. S100.STG: 1,321 dialogues, SG00.STG: 2,445 dialogues.

### S100.STG Results

| Chunk | VLUT Offset | Patched | Skipped | Korean Bytes |
|-------|-------------|---------|---------|--------------|
| 0 | 0xA0800 | 144 | 1 | 4,222 |
| 1 | 0xA3D00 | 159 | 1 | 4,803 |
| 2 | 0xA0500 | 18 | 2 | 393 |
| 3 | 0xA0100 | 95 | 6 | 2,390 |
| 4 | 0xA9500 | 406 | 3 | 9,067 |
| 5 | 0xAA400 | 114 | 1 | 2,774 |
| 6 | 0xA2E00 | 48 | 1 | 894 |
| 7 | 0xA0100 | 31 | 0 | 605 |
| 8 | N/A | 0 | 75 | (no space) |
| 9 | 0xA0100 | 38 | 2 | 771 |
| **Total** | | **1,053** | **92** | **25,919** |

Only chunk 8 has no safe padding space - it uses fixed-length fallback.

**Note**: Chunk 4 uses a 20KB gap at 0xA9500-0xAE800 (between two data regions).

## Feasibility Analysis

### Available Resources

| Resource | Available | Required | Status |
|----------|-----------|----------|--------|
| Lookup table space | 50-64KB per chunk | ~8KB | **Sufficient** |
| Handler patch space | ~100 bytes | ~60 bytes | **Tight but doable** |
| SCPS_100.26 code space | Limited | Trampoline | **Need hook** |

### Key Components Identified

| Component | Location | Status |
|-----------|----------|--------|
| Text advance handler | 0x80101560 | **Found** |
| Jump table | 0x80183B60 | **Found** |
| State structure | $s0/$s1 pointer | **Documented** |
| TextPtr field | +0x78 | **Identified** |
| SeqIndex field | +0x9A | **Identified** |
| Padding region | Chunk +0xA0000 | **Verified free** |

## Implementation Phases

### Phase 1: Proof of Concept (1 chunk) - COMPLETE

**Goal**: Demonstrate lookup table approach works.

**Status**: **VERIFIED WORKING** (2026-02-06)

**Implementation**:

1. **Passthrough Hook Test** (`python/poc_hook_test.py`)
   - Minimal trampoline that just calls original handler
   - Verified hook mechanism doesn't break the game
   - Result: Game works normally

2. **Lookup Table Hook** (`python/poc_chunk_table.py`)
   - Full trampoline with table lookup logic (192 bytes)
   - Lookup table stored in STG chunk at offset 0xA0800 (2048 bytes for 510 dialogues)
   - Result: Game works normally with lookup redirection

**Key Discovery**: Chunk base calculation works with `TextPtr & 0xFFF00000` (1MB alignment).

**Scripts Created**:
| Script | Purpose |
|--------|---------|
| `python/poc_hook_test.py` | Generate passthrough hook for testing |
| `python/poc_chunk_table.py` | Generate lookup table and trampoline |
| `python/apply_hook.py` | Apply hook to already-patched SCPS_100.26 |
| `python/add_lookup_table.py` | Add lookup table to already-patched S100.STG |

**Lookup Table Format** (at chunk offset 0xA0800):
```c
struct LookupTable {
    char     magic[4];      // "VLUT" (0x54554C56 LE)
    uint32_t entry_count;   // Number of dialogues
    uint32_t offsets[];     // Relative to text region start
};
```

**Trampoline Logic - Multi-Chunk** (188 bytes at RAM 0x80199654):
```c
void trampoline(State* state) {
    // Calculate chunk base from TextPtr
    uint32_t chunk_base = state->TextPtr & 0xFFF00000;

    // Read VLUT offset from master pointer at 0xAFF00
    uint32_t vlut_offset = *(uint32_t*)(chunk_base + 0xAFF00);

    // Find lookup table at per-chunk offset
    LookupTable* table = (LookupTable*)(chunk_base + vlut_offset);

    // Validate magic
    if (table->magic != "VLUT") {
        original_handler(state);  // Fallback
        return;
    }

    // Bounds check
    uint16_t index = state->SeqIndex;
    if (index >= table->entry_count) {
        original_handler(state);  // Fallback
        return;
    }

    // Lookup and update TextPtr
    // Offsets are relative to chunk start (not text region)
    uint32_t offset = table->offsets[index];
    state->TextPtr = chunk_base + offset;
    state->SeqIndex++;
}
```

**Recommended Workflow (using orchestrator)**:
```bash
# Run complete workflow automatically
python python/patch/patch_workflow.py S100 SG00
```

**Manual Workflow**:
```bash
# 1. Patch Korean font and fixed-length text
python python/patch/patch_all.py

# 2. Apply variable-length patching with per-chunk VLUTs
python python/patch/patch_variable_length_multi.py S100

# 3. Apply multi-chunk hook to SCPS_100.26
python python/patch/apply_hook.py --variable-length-multi

# 4. Apply to disc image
python python/patch/patch_bin.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
```

### Phase 2: Full Chunk Support - COMPLETE

**Goal**: Support all chunks in an STG file.

**Status**: **WORKING** (2026-02-06)

**Implementation**:
- Per-chunk VLUT offsets based on where actual data ends
- Master pointer at 0xAFF00 tells trampoline where to find VLUT
- Template-driven dialogue extraction using `decode_text.py:scan_stg()`

**Per-Chunk VLUT Offsets** (S100.STG, 11 chunks):
```python
VLUT_OFFSETS_S100 = {
    0: 0xA0800,   # 63KB available
    1: 0xA3D00,   # 50KB available
    2: 0xA0500,   # 64KB available
    3: 0xA0100,   # 65KB available
    4: 0xA9500,   # 20KB gap between data regions
    5: 0xAA400,   # 23KB available
    6: 0xA2E00,   # 54KB available
    7: 0xA0100,   # 65KB available
    8: 0,         # NO SPACE - data to 0xAFFFF
    9: 0xA0100,   # 65KB available
    10: 0xAD400,  # 11KB available
}
```

**Per-Chunk VLUT Offsets** (SG00.STG, 56 chunks):
```python
VLUT_OFFSETS_SG00 = {
    0: 0,         # NO SPACE
    2: 0xA0100,   # 65KB available
    7: 0xA9800,   # 22KB available
    12: 0xAB500,  # 19KB available
    13-20: 0xA0100-0xAE900,  # Various offsets
    21: 0xAE900,  # 6KB available
    23: 0xA0100,  # 65KB available
    25-30: 0xA0100-0xA4100,  # Various offsets
    32: 0xA0100,  # 65KB available
    34-38: 0xA0100-0xA8C00,  # Various offsets
    41-45: 0xA0100-0xA0300,  # Various offsets
    47-51: 0xA0100-0xA7C00,  # Various offsets
    54-55: 0xA1E00-0xA2E00,  # 56KB and 54KB available
    # Chunks 0, 4, 5, 6, 8-11, 22, 24, 31, 39, 40, 46, 53 have NO SPACE
}
```

### Phase 3: All STG Files - COMPLETE

**Goal**: Support all 19 STG files.

**Status**: **ALL STG FILES SUPPORTED** (2026-02-09)

**Steps**:
1. ~~Analyze padding region for each STG file's chunks~~ **DONE for S100, SG00, S200**
2. ~~Generate VLUT offset tables for all files~~ **DONE** (hardcoded for S100/SG00/S200, auto-detected for rest)
3. ~~Comprehensive testing across all files~~ **DONE**

**SG00.STG Results** (56 chunks, 43MB):

| Chunk | VLUT Offset | Patched | Skipped | Notes |
|-------|-------------|---------|---------|-------|
| 0 | N/A | 0 | 4 | No space |
| 2 | 0xA0100 | 55 | 0 | |
| 4-6 | N/A | 0 | 319 | No space |
| 7 | 0xA9800 | 119 | 0 | |
| 8-11 | N/A | 0 | 70 | No space |
| 12 | 0xAB500 | 95 | 0 | |
| 21 | 0xAE900 | 23 | 0 | |
| 22 | N/A | 0 | 74 | No space |
| 23 | 0xA0100 | 29 | 0 | |
| 24 | N/A | 0 | 44 | No space |
| 27-30 | 0xA0100-0xA2500 | 76 | 0 | |
| 31 | N/A | 0 | 42 | No space |
| 32 | 0xA0100 | 36 | 0 | |
| 34 | 0xA8C00 | 27 | 0 | |
| 39-40 | N/A | 0 | 90 | No space |
| 41-45 | 0xA0100-0xA0300 | 112 | 0 | |
| 46 | N/A | 0 | 54 | No space |
| 47-51 | 0xA0100-0xA7C00 | 73 | 0 | |
| 53 | N/A | 0 | 88 | No space |
| 54 | 0xA1E00 | 58 | 0 | |
| **Total** | | **685** | **785** | |

**Chunks without padding space (15 total)**: 0, 4, 5, 6, 8, 9, 10, 11, 22, 24, 31, 39, 40, 46, 53

These chunks use fixed-length fallback (original text region)

**Per-Chunk VLUT Offsets** (S200.STG, 17 chunks):
```python
VLUT_OFFSETS_S200 = {
    1: 0xA0100,
    2: 0xA0F00,
    3: 0xA2800,
    4: 0xA7100,
    6: 0xA0100,
    7: 0xADC00,
    8: 0xA0100,
    11: 0xA9000,
    12: 0xA0100,
    13: 0xA9E00,
    # Chunks 0, 5, 9, 10, 14, 15, 16 have NO SPACE
}
```

**S200.STG Results** (17 chunks, 13MB):

| Chunk | VLUT Offset | Patched | Skipped | Notes |
|-------|-------------|---------|---------|-------|
| 0 | N/A | 0 | 249 | No space |
| 1 | 0xA0100 | 200 | 23 | |
| 2 | 0xA0F00 | 25 | 0 | |
| 3 | 0xA2800 | 392 | 5 | |
| 4 | 0xA7100 | 163 | 14 | |
| 5 | N/A | 0 | 94 | No space |
| 6 | 0xA0100 | 45 | 0 | |
| 7 | 0xADC00 | 33 | 35 | Tight space (~5KB) |
| 8 | 0xA0100 | 70 | 3 | |
| 9 | N/A | 0 | 53 | No space |
| 10 | N/A | 0 | 85 | No space |
| 11 | 0xA9000 | 121 | 13 | |
| 12 | 0xA0100 | 11 | 0 | |
| 13 | 0xA9E00 | 44 | 14 | |
| 14 | N/A | 0 | 114 | No space |
| 15 | N/A | 0 | 80 | No space |
| 16 | N/A | 0 | 154 | No space |
| **Total** | | **1,104** | **936** | |

**Chunks without padding space (7 total)**: 0, 5, 9, 10, 14, 15, 16

### Phase 4: Auto-Detection & Patcher Integration - COMPLETE

**Goal**: Seamless patching workflow for all STG files without manual offset tables.

**Status**: **COMPLETE** (2026-02-09)

**Implementation**: `auto_detect_vlut_offsets()` in `patch_variable_length_multi.py`

**How it works**:
1. Scans each chunk's padding region (0xA0000-0xB0000) in 256-byte blocks
2. Identifies which blocks are all-zero (free space)
3. Finds the largest contiguous run of free blocks per chunk
4. Requires minimum 8KB (0x2000) for VLUT + Korean text storage
5. If the free region doesn't extend to 0xB0000 (data exists after the gap), records the end boundary to prevent overwriting

**Unified API**: `get_vlut_config(stg_name, data)` returns `(vlut_offsets, korean_text_ends)`:
- **S100/SG00/S200**: Returns hardcoded, manually verified tables (unchanged)
- **All other STGs**: Calls `auto_detect_vlut_offsets()` to scan the raw data

**Auto-detection accuracy** (validated against hardcoded S100 offsets):
- Correctly identifies all free regions (within 1 block of manually set offsets)
- Correctly identifies chunk 4's inter-data gap (exact match at 0xA9500)
- Correctly identifies chunk 8 as having no space (exact match)
- Correctly detects end boundaries for partial free regions (chunk 4: 0xAE800)

**Diagnostic output** for auto-detected STGs:
```
Auto-detected VLUT placement for 8/17 chunks:
  Chunk  1: VLUT=0xa0000  avail=60KB
  Chunk  6: VLUT=0xa0000  avail=60KB
  Chunk  8: VLUT=0xa0000  avail=60KB
  ...
```

### VLUT Space Survey (All 19 STG Files)

Auto-detection scan results across all STG files (2026-02-09):

**315 / 382 chunks have free space for VLUT (82%)**. 67 chunks use fixed-length fallback.

| STG | Chunks | With Space | Without | Coverage |
|-----|--------|-----------|---------|----------|
| S100 | 11 | 10 | 1 | 91% |
| S200 | 17 | 10 | 7 | 59% |
| S300 | 11 | 9 | 2 | 82% |
| S400 | 10 | 9 | 1 | 90% |
| S500 | 12 | 11 | 1 | 92% |
| S600 | 16 | 11 | 5 | 69% |
| S700 | 34 | 30 | 4 | 88% |
| S800 | 16 | 13 | 3 | 81% |
| S900 | 14 | 13 | 1 | 93% |
| SA00 | 15 | 12 | 3 | 80% |
| SB00 | 10 | 8 | 2 | 80% |
| SC00 | 20 | 17 | 3 | 85% |
| SD00 | 18 | 15 | 3 | 83% |
| SE00 | 20 | 16 | 4 | 80% |
| SF00 | 47 | 44 | 3 | 94% |
| SG00 | 56 | 36 | 20 | 64% |
| SH00 | 16 | 16 | 0 | **100%** |
| SI00 | 39 | 35 | 4 | 90% |
| SJ00 | 0 | — | — | — |
| **Total** | **382** | **315** | **67** | **82%** |

**Key observations**:
- **SH00** is the only file with 100% coverage (all 16 chunks have space)
- **SG00** has the most no-space chunks (20/56), concentrated in chunks 0-11
- **SJ00** is empty (0 bytes, 0 chunks)
- Most chunks with space have **60KB available** (entire 0xA0000-0xB0000 is zeros)
- Some chunks have partial free regions with end boundaries:

| STG | Chunk | VLUT | Available | End | Notes |
|-----|-------|------|-----------|-----|-------|
| S100 | 4 | 0xA9500 | 16KB | 0xAE800 | Gap between two data regions |
| S400 | 0 | 0xA5500 | 35KB | 0xAF200 | Data after gap |
| S700 | 21 | 0xAA000 | 9KB | 0xAD600 | Data after gap |
| S800 | 3 | 0xA2400 | 41KB | 0xAD800 | Data after gap |
| SA00 | 0 | 0xA2800 | 43KB | 0xAE400 | Data after gap |
| SB00 | 7 | 0xA3500 | 38KB | 0xAE000 | Data after gap |
| SD00 | 6 | 0xA0000 | 55KB | 0xAED00 | Data after gap |
| SF00 | 7 | 0xA4700 | 29KB | 0xACC00 | Data after gap |
| SF00 | 8 | 0xA7100 | 28KB | 0xAF200 | Data after gap |
| SF00 | 12 | 0xAB700 | 6KB | 0xAE100 | Data after gap |
| SG00 | 41 | 0xA0000 | 47KB | 0xACC00 | Dialogues in padding |
| SI00 | 13 | 0xA3400 | 37KB | 0xAD900 | Data after gap |

These chunks have non-zero data after the free region; `korean_text_ends` prevents overwriting it.

## How Variable-Length Translation Works

### The Problem with Fixed-Length

Fixed-length patching overwrites Japanese text in-place:
```
Original:  [A9 00][prefix][Japanese text (30 bytes)][00]
Patched:   [A9 00][prefix][Korean text (30 bytes max)][00]  ← TRUNCATED if longer
```

Korean translations are often longer than Japanese, causing truncation:
```
Original Japanese (30 bytes):
┌──────────────────────────────────────────┐
│ あるでぃあふらぐにみょうな値がはいっとる │
└──────────────────────────────────────────┘

Korean Translation (45 bytes) - TRUNCATED:
┌──────────────────────────────────────────┐
│ 알디아 플래그에 이상한 값이 들어있       │ ← Cut off!
└──────────────────────────────────────────┘
```

### The Solution: Relocate to Padding Region

Instead of overwriting, we store Korean text in the unused padding region and use a lookup table (VLUT) to redirect the game:

```
Chunk Structure (772,096 bytes):

0x00000 ┌─────────────────────────────────────┐
        │ Graphics (sprites, tiles, etc.)    │
0x70000 ├─────────────────────────────────────┤
        │ MIPS code (scene-specific)          │
0x80000 ├─────────────────────────────────────┤
        │ MIPS code (main logic)              │
0xA0000 ├─────────────────────────────────────┤◄── Padding region start
        │ ┌─────────────────────────────────┐ │
        │ │ VLUT Table                      │ │◄── We write here
        │ │ - Magic "VLUT"                  │ │
        │ │ - Offset entries for dialogues  │ │
        │ └─────────────────────────────────┘ │
        │ ┌─────────────────────────────────┐ │
        │ │ Korean Text Storage             │ │◄── We write here
        │ │ [A9 00][prefix]큰 도시네[00]     │ │
        │ │ [A9 00][prefix]알디아의 수도[00] │ │
        │ │ ... (full-length dialogues)     │ │
        │ └─────────────────────────────────┘ │
        │ ┌─────────────────────────────────┐ │
        │ │ Master Pointer at 0xAFF00       │ │◄── Points to VLUT
        │ └─────────────────────────────────┘ │
0xB0000 ├─────────────────────────────────────┤
        │ Event scripts                       │
0xB4000 ├─────────────────────────────────────┤
        │ Original Japanese (untouched)       │
0xBC800 └─────────────────────────────────────┘
```

### VLUT Table Structure

```
VLUT Table Layout:
┌────────────────────────────────────────────────────────┐
│ Offset 0x00: [56 4C 55 54]  Magic "VLUT" (4 bytes)     │
│ Offset 0x04: [A3 00 00 00]  Entry count (4 bytes)      │
├────────────────────────────────────────────────────────┤
│ Offset 0x08: [18 A6 00 00]  Entry 0: offset 0xA618     │
│ Offset 0x0C: [3A A6 00 00]  Entry 1: offset 0xA63A     │
│ Offset 0x10: [5C A6 00 00]  Entry 2: offset 0xA65C     │
│ ...                                                     │
└────────────────────────────────────────────────────────┘
```

Each entry is a **4-byte offset from chunk start**:
- **Translated dialogues**: Point to Korean text in padding region (0xA0000-0xAFFFF)
- **Untranslated dialogues**: Point to original Japanese in text region (0xB4000+)

### How the Trampoline Uses VLUT

```c
// Game calls text handler, we intercept via jump table
void trampoline(State* state) {
    // 1. Calculate chunk base (1MB alignment)
    uint32_t chunk_base = state->TextPtr & 0xFFF00000;

    // 2. Read VLUT offset from master pointer
    uint32_t vlut_offset = *(uint32_t*)(chunk_base + 0xAFF00);

    // 3. Find VLUT table
    LookupTable* table = (LookupTable*)(chunk_base + vlut_offset);

    // 4. Validate magic "VLUT"
    if (table->magic != 0x54554C56) {
        original_handler(state);  // Fallback
        return;
    }

    // 5. Look up offset for current dialogue
    uint32_t offset = table->offsets[state->SeqIndex];

    // 6. Redirect TextPtr to Korean text
    state->TextPtr = chunk_base + offset;
    state->SeqIndex++;
}
```

### The Advantage

With variable-length, Korean text has **no size limit**:

| Mode | Truncated Dialogues | Result |
|------|---------------------|--------|
| Fixed-length | 85 out of 1,151 | Text cut off mid-sentence |
| Variable-length | **0** out of 1,053 | Full translations displayed |

Translators have freedom to write natural Korean without worrying about character limits!

## Technical Details

### Hook Implementation

**Option A: Direct patch** (Recommended)
```mips
; At 0x80101560, replace first instruction:
0x80101560: j     trampoline      ; Jump to our code
0x80101564: nop                   ; Delay slot

; Trampoline code (in chunk padding or unused EXE space):
trampoline:
    ; Save registers
    addiu $sp, $sp, -16
    sw    $t0, 0($sp)
    sw    $t1, 4($sp)

    ; Load table base from known location
    lui   $t0, TABLE_HI
    ori   $t0, $t0, TABLE_LO

    ; Get current index
    lhu   $t1, 0x9A($s1)

    ; Lookup: ptr = table[index]
    sll   $t1, $t1, 2
    addu  $t0, $t0, $t1
    lw    $t0, 0($t0)

    ; Store new text pointer
    sw    $t0, 0x78($s1)

    ; Restore and return to original code
    lw    $t1, 4($sp)
    lw    $t0, 0($sp)
    addiu $sp, $sp, 16
    j     0x80101564 + 4    ; Continue after hook
    nop
```

**Option B: Caller hook**
Patch one of the 112 callers of 0x80101560 to call our wrapper instead.

### Table Location

The lookup table will be placed at chunk offset 0xA0800 (after the ~0x700 bytes of actual data at 0xA0000).

Each chunk's table is independent and loaded with the chunk.

### Chunk Base Address

The trampoline needs to know the current chunk's base address in RAM. Options:
1. Store in a known RAM location when chunk loads
2. Calculate from existing pointers in state structure
3. Use relative addressing if table is in same chunk

## Branch Offset Debugging (2026-02-06)

### The Problem

After implementing the VLUT lookup trampoline, the game froze immediately after loading a scene. The passthrough hook worked fine, confirming the hook mechanism itself was correct.

### Root Cause

The MIPS branch instructions had incorrect offset values. In MIPS, branch offset is calculated as:

```
offset = target_instruction_index - (branch_instruction_index + 1)
```

The original code had wrong offsets that caused branches to jump to incorrect locations (middle of other instructions or data).

### Trampoline Instruction Layout (Fixed-Length Mode)

```
Index  Instruction              Purpose
-----  -----------------------  ---------------------------
0-3    Prologue                 Save registers
4      lw $v0, 0x78($a0)        Load TextPtr
5-6    Chunk base calc          Mask to 1MB alignment
7      Save chunk base          Store in $t2
8-10   Table address calc       chunk_base + 0xA0800
11     Load magic               Read first 4 bytes
12-13  Build expected magic     0x54554C56 ("VLUT")
14     BRANCH 1                 bne → fallback if magic mismatch
15     nop
16     Load entry count
17-18  Load SeqIndex
19     Bounds check             slt
20     BRANCH 2                 beq → fallback if out of bounds
21     nop
22-24  Entry address calc
25     BRANCH 3                 beq → fallback if offset invalid
26     nop
27-30  TEXT_REGION add          (4 instructions for fixed-length)
31     Update TextPtr
32-34  Increment SeqIndex
35-39  Success epilogue         Restore and return
40+    Fallback code            Call original handler
```

### Correct Branch Offsets

**Fixed-length mode** (fallback at index 40):
| Branch | Index | Offset Calculation | Hex Value |
|--------|-------|-------------------|-----------|
| Branch 1 | 14 | 40 - 15 = 25 | 0x19 |
| Branch 2 | 20 | 40 - 21 = 19 | 0x13 |
| Branch 3 | 25 | 40 - 26 = 14 | 0x0E |

**Variable-length mode** (fallback at index 36, 4 fewer instructions):
| Branch | Index | Offset Calculation | Hex Value |
|--------|-------|-------------------|-----------|
| Branch 1 | 14 | 36 - 15 = 21 | 0x15 |
| Branch 2 | 20 | 36 - 21 = 15 | 0x0F |
| Branch 3 | 25 | 36 - 26 = 10 | 0x0A |

### Debugging Methodology

1. Passthrough hook test → Game works (confirms hook mechanism is sound)
2. VLUT lookup hook → Game freezes (problem is in trampoline logic)
3. Manual instruction count of trampoline code
4. Recalculate branch offsets based on actual indices
5. Fix applied and retested

### Lesson Learned

When writing MIPS assembly by hand, always:
1. Number each instruction with its index
2. Identify all branch targets
3. Calculate offsets using: `target - (branch + 1)`
4. Verify by counting instructions between branch and target

## Risks

### Risk: Incomplete understanding
**Mitigation**: Extensive testing on emulator with save states.

### Risk: Other code depends on TextPtr
**Mitigation**: TextPtr still updated, just with looked-up value.

### Risk: Performance impact
**Mitigation**: Lookup is O(1), minimal overhead.

### Risk: Save game compatibility
**Mitigation**: State structure unchanged, saves should work.

## Alternative Approaches

### If hook is too complex

**Simplified approach**: Text compression
- Use shorter synonyms in translations
- Implement abbreviation dictionary
- Target 95% fit rate instead of 100%

This is less technical but requires more translation work.

### If RAM constraints hit

**Reduce table size**:
- Use 2-byte offsets instead of 4-byte (text region is <64KB)
- Compress entries with delta encoding
- This would halve table size to ~4KB per chunk

## Next Steps

1. ~~**Phase 1**: Implement proof of concept~~ **DONE**
2. ~~**Phase 2**: Extend to all chunks~~ **DONE** (S100: 11 chunks)
3. ~~**Phase 3**: Enable actual variable-length translations~~ **DONE** (all 19 STG files)
4. ~~**Phase 4**: Auto-detection & patcher integration~~ **DONE** (auto-detect for S300-SJ00)
5. **Phase 5**: Add translations for remaining STG files (S300-SJ00)
6. **Phase 6**: Integrate remaining STGs into `patch_workflow.py`

## Known Issues

### Chunks Without Padding Space (4 and 8)

**Problem**: Chunks 4 and 8 in S100.STG have data filling the entire padding region (0xA0000-0xAFFFF), leaving no space for VLUT tables.

**Why Cross-Chunk Storage Won't Work**:
- The game loads **ONE chunk at a time** into RAM at the same base address
- When chunk 4 is loaded, chunk 0's data is **replaced** - it's no longer in RAM
- The trampoline reads VLUT from `chunk_base + offset`, so it can only access data within the currently loaded chunk
- Storing chunk 4's VLUT in chunk 0's space would fail because that data isn't present when chunk 4 is active

**Potential Solutions**:

| Approach | Pros | Cons | Status |
|----------|------|------|--------|
| Store VLUT in SCPS_100.26 | Always in RAM | Limited space (~600 bytes), complex indexing | Not implemented |
| Expand STG file | Clean solution | May break chunk loading | Not tested |
| Compress/relocate padding data | Uses existing space | Need to understand data format | Under investigation |
| Fixed-length fallback | Simple, working | Dialogues may truncate | **Current** |

**Data Analysis Results** (2026-02-06):

**Chunk 4**: Has a **20KB zero gap** at `0xA94EA - 0xAE87C`!
- Data regions: 0xA0000-0xA9500 (sprite/animation tables) and 0xAE900-0xB0000
- Gap is unused and safe for VLUT + Korean text
- **Solution**: Use offset 0xA9500 for VLUT (20KB available)

**Chunk 8**: Fully packed, no usable gaps
- Entire 64KB region contains continuous data (entropy 6.44 bits/byte)
- 894 `FFFF` terminators suggest complex structured records
- RLE compression makes it larger (186%) - incompressible
- **No solution yet**: Must use fixed-length fallback

### Line Break Encoding (TO BE REVISITED)
- `[br]` tags in translations are NOT being encoded
- Attempted to encode as `FF 05 01 01` but caused game crashes
- Need investigation: likely buffer overflow or offset mismatch

### Orphan Menu Texts - FIXED (2026-02-06)

**Problem**: Menu options (yes/no prompts, tutorial menus, system prompts) were not being translated because they weren't captured by the decoder.

**Root Cause**: These texts use `A9 00` markers but have NO associated 48-byte templates. Template-driven extraction only finds dialogues referenced by templates.

**Solution**: Added orphan menu detection pass to `decode_text.py:scan_stg()`:
- Scans text region for `A9 00` markers not already captured
- Validates text contains `[br][opt]` pattern (real menu = options on separate lines)
- Filters out: bounty tables using `[opt]` as column separators, dialogue pauses
- Assigns context opcode `0x00A9` for identification

**Results** (S100.STG):
- 76 real orphan menus (filtered from 97 raw texts)
- Filtered out: 7 bounty tables, 9 dialogue pauses, 5 other false positives
- Categories: tutorial menus, yes/no prompts, system prompts, navigation

**Action Required**:
1. Regenerate decoded output to include orphan menus
2. Add translations for orphan menu texts to translation file
3. Re-run variable-length patcher

### Bare Dialogue Detection (2026-02-07)

**Problem**: Location names, battle messages, and scene announcements were not being captured.

**Root Cause**: These texts use `A9 00` markers with kanji content but have NO templates AND NO `[opt]` tags.

**Solution**: Added bare dialogue detection pass to `decode_text.py:scan_stg()`:
- Scans text region for `A9 00` markers not already captured by template or orphan menu passes
- Validates text contains kanji (real Japanese text)
- Must have at least 3 characters and pass garbage filter
- Assigns context opcode `0x00B4` for identification

**Results**:
- S100.STG: 40 bare dialogues (location names, battle messages)
- SG00.STG: 377 bare dialogues

**Examples**:
- Location names: コルボ平原, ラウス平野
- Battle messages: 戦闘に参加するキャラクターを選んで下さい
- Scene announcements: 持ち場につけ！

### Complete Dialogue Type Summary (2026-02-07)

| Type | Context Opcode | Region | Detection | S100 | SG00 |
|------|----------------|--------|-----------|------|------|
| Template-associated | 0xFFFE/0x80XX | 0xB4000-0xBC7FF | 48-byte template | 1,165 | 1,495 |
| Bare dialogues | 0x00B4 | 0xB4000-0xBC7FF | A9 00 + kanji | 40 | 377 |
| Orphan menus | 0x00A9 | 0xB4000-0xBC7FF | `[br][opt]` pattern | 76 | 403 |
| Event Script | 0x00B0 | 0xB0000-0xB4000 | A9 00 + validation | 33 | 144 |
| Padding | 0x00A0 | 0xA0000-0xB0000 | A9 00 + validation | 7 | 26 |
| **Total** | | | | **1,321** | **2,445** |

## Files

| Purpose | Path |
|---------|------|
| This document | `docs/VARIABLE_LENGTH_IMPLEMENTATION.md` |
| **Multi-chunk patcher** | `python/patch_variable_length_multi.py` |
| Apply hook utility | `python/apply_hook.py` |
| Fixed-length patcher | `python/patch_all.py` |
| Dialogue decoder | `python/decode/decode_text.py` |
| Interpreter analysis | `docs/INTERPRETER_ANALYSIS.md` |
| Dialogue system analysis | `docs/DIALOGUE_SYSTEM_ANALYSIS.md` |
