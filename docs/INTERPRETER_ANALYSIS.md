# Event Script Interpreter Analysis - Arc the Lad 2

## Overview

This document describes the reverse-engineering of the event script interpreter in SCPS_100.26 that handles dialogue reading. The goal is to understand how to enable variable-length Korean translations.

## Key Findings

### State Structure

The dialogue system uses a state structure (pointed to by $s0/$s1) with the following key fields:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x34 | 4 | Flags | State flags (bitfield) |
| 0x70 | 1 | StateIndex | Current state machine index (selects handler) |
| 0x71 | 1 | CommandType | Current command/stream type (e.g., 0xA9, 0x67) |
| 0x74 | 1 | SubState | Sub-state flag |
| 0x78 | 4 | **TextPtr** | Current text stream pointer |
| 0x98 | 2 | Unknown | Control field |
| 0x9A | 2 | **SeqIndex** | Dialogue sequence counter |

### Handler Dispatch System

**Command Dispatcher**: `RAM 0x80173300 (File 0x0B2700)`
- Compares command byte ($a1) with values: 0x63, 0x66, 0x67, 0x6A, etc.
- Command 0x67 branches to `0x801739A4`

**State Machine Dispatch**: `RAM 0x801025B8 (File 0x0419B8)`
- Commands 0xA9 and 0x67 share the same handler path
- Uses StateIndex (offset 0x70) as index into jump table
- Jump table at `RAM 0x80183B60` contains 19 handler pointers

**Key Handler**: `RAM 0x80101560 (File 0x040960)`
- Advances text pointer through the stream
- Increments sequence counter

### Text Pointer Advancement (0x80101560)

```mips
; Load current text pointer
0x801015B4: lw    $a0, 0x78($s1)      ; $a0 = state->TextPtr

; Calculate advance amount
0x801015B0: sll   $v0, $a1, 1         ; $v0 = advance * 2 (characters?)

; Update text pointer
0x801015BC: addu  $v0, $v0, $a0       ; $v0 = TextPtr + advance
0x801015C4: sw    $v0, 0x78($s1)      ; state->TextPtr = $v0

; Update sequence counter
0x801015B8: lhu   $v1, 0x9A($s1)      ; $v1 = state->SeqIndex
0x801015C0: addu  $v1, $v1, $a1       ; $v1 += advance
0x801015D4: sh    $v1, 0x9A($s1)      ; state->SeqIndex = $v1
```

**Critical Insight**: The text pointer advances by a calculated amount, not by seeking to a specific offset. The advance amount comes from a lookup table at `0x80183880`.

### Jump Table at 0x80183B60

| Index | Handler | Purpose |
|-------|---------|---------|
| 0 | 0x80101AC4 | ? |
| 1 | 0x80101914 | ? |
| 2 | 0x80104860 | Flag check |
| 3 | 0x80105644 | ? |
| 4 | 0x801055D8 | ? |
| 5 | 0x80101560 | **Text advance** |
| 6 | 0x80102B84 | ? |
| ... | ... | ... |

Handler #5 (0x80101560) is the text pointer advancement handler.

## Modification Approach

### Goal
Enable variable-length translations by redirecting text reads to different offsets.

### Approach 1: Lookup Table Redirect (Recommended)

**Concept**: Replace sequential pointer advancement with table lookup.

**Current flow**:
```
NextDialogue:
  ptr = ptr + advance
  ReadText(ptr)
```

**Modified flow**:
```
NextDialogue:
  index++
  ptr = LookupTable[stream_id][index]
  ReadText(ptr)
```

**Requirements**:
1. Create lookup table in unused RAM (~4 bytes × 2000 dialogues = 8KB)
2. Patch handler at 0x80101560 to use table
3. Initialize table at chunk load time

### Approach 2: Inline Offset Format

**Concept**: Modify text format to include explicit next-dialogue offset.

**Current format**:
```
[A9 00] [text bytes] [00]
```

**Modified format**:
```
[A9 00] [2-byte next_offset] [text bytes] [00]
```

The handler would read the offset and jump to it.

**Requirements**:
1. Modify text region format
2. Patch handler to read offset field
3. Less RAM needed but more intrusive

### Available RAM for Patches

| Region | Address | Size | Notes |
|--------|---------|------|-------|
| BSS End | 0x801FC834 | ~14KB | Before stack, may conflict |
| Chunk Padding | +0xA0000 | 64KB | 98% zeros, per-chunk |

The chunk padding region at offset 0xA0000 (64KB of mostly zeros) is the best candidate for a per-chunk lookup table.

## Implementation Steps

### Phase 1: Create Trampoline

The handler at 0x80101560 is only ~100 bytes. Patch options:
1. **Hook start**: Replace first instruction with jump to custom code
2. **Hook call**: Patch one of the 112 callers to call custom wrapper

**Trampoline location**: Could use the padding region or find unused code space.

### Phase 2: Lookup Table

Create structure:
```c
struct DialogueLookup {
    uint32_t offsets[MAX_DIALOGUES];  // Text region offsets
    uint16_t count;                    // Number of entries
    uint16_t stream_id;                // Stream identifier
};
```

Per-chunk: ~2000 dialogues × 4 bytes = 8KB per chunk.

### Phase 3: Patch Handler

Replace the advance logic:
```mips
; Original
lw    $a0, 0x78($s1)
sll   $v0, $a1, 1
addu  $v0, $v0, $a0
sw    $v0, 0x78($s1)

; Patched
lw    $a0, 0x78($s1)       ; Keep for compatibility
lhu   $v0, 0x9A($s1)       ; Get current index
sll   $v0, $v0, 2          ; index * 4
lw    $t0, TABLE_BASE      ; Load table base
addu  $t0, $t0, $v0        ; &table[index]
lw    $v0, 0($t0)          ; new_ptr = table[index]
sw    $v0, 0x78($s1)       ; Update pointer
; Continue to increment index as normal
```

### Phase 4: Table Generation

The patcher needs to:
1. Parse Korean translations with variable lengths
2. Calculate new text offsets
3. Generate lookup table
4. Write table to chunk padding region
5. Patch main executable

## Risks and Challenges

### RAM Constraints
- PS1 has only 2MB RAM
- Lookup tables (~8KB per chunk) must fit somewhere
- BSS/stack regions may conflict

### Multiple Chunks
- Each STG chunk needs its own table
- Table must be initialized when chunk loads
- Main executable patch must handle any chunk

### State Preservation
- Must not corrupt existing state structure
- Other code may depend on TextPtr value
- Sequence counter must remain valid

### Testing
- Extensive testing needed across all 19 STG files
- Save/load compatibility
- Battle transitions

## Next Steps

1. Find exact unused RAM regions in loaded chunk
2. Determine hook point (start of handler vs caller)
3. Write proof-of-concept for one chunk
4. Expand to full implementation

## Files Reference

| File | Location |
|------|----------|
| Main executable | SCPS_100.26 |
| Handler function | 0x80101560 (file 0x040960) |
| Jump table | 0x80183B60 (file 0x0C2F60) |
| Advance lookup | 0x80183880 (file 0x0C2C80) |
| Text region | STG +0xB4000 |
| Chunk padding | STG +0xA0000 |
