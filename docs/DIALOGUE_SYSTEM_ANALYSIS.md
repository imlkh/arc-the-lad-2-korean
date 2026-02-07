# Dialogue System Analysis - Arc the Lad 2

Complete reverse-engineering analysis of how the game reads and displays dialogues.

## Executive Summary

**Conclusion:** Variable-length patching via interpreter hook is now working. Fixed-length patching remains available as a fallback.

| Approach | Status | Reason |
|----------|--------|--------|
| Variable-length (VLUT) | **WORKING** | Interpreter hook redirects TextPtr to Korean text in padding region |
| Fixed-length patching | **WORKING** | Replace text in-place, truncate if too long (fallback) |
| MIPS code modification | **NOT FEASIBLE** | No direct address references to text region |
| Script prefix redirection | **NOT FEASIBLE** | Prefix is metadata, not a lookup key |
| Text relocation | **NOT FEASIBLE** | Event script uses sequential streams, not pointers |
| Reflow mode | **BROKEN** | Template pointer recalculation causes game crashes |

## Dialogue Reading Model

### Stream-Based Sequential Reading

The game uses a **stream-based sequential reading model** for dialogues:

```
                    Event Script Engine
                           │
                           ▼
              ┌────────────────────────┐
              │   0x0067 Command       │
              │   with ref_id = 0xA9   │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Read NEXT dialogue    │
              │  from A9 stream        │
              └────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────┐
    │  A9 Stream (Text Region 0xB4000+)        │
    │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐        │
    │  │ D1  │→│ D2  │→│ D3  │→│ D4  │→ ...   │
    │  └─────┘ └─────┘ └─────┘ └─────┘        │
    │     ▲                                    │
    │     └── Stream position pointer          │
    └──────────────────────────────────────────┘
```

### Key Characteristics

1. **Multiple dialogue streams** exist, identified by reference IDs (A9, AA, AB, 66)
2. **Sequential reading**: Each `0x0067` command reads the NEXT dialogue from its stream
3. **Position tracking**: Game maintains position pointers for each stream
4. **No random access**: Cannot jump to arbitrary dialogues within a stream
5. **Inline text**: Dialogues are embedded directly after `A9 00` markers

### Dialogue Stream Format

Non-template dialogues use this inline format:

```
[A9 00] [2-byte script prefix] [text bytes...] [00 null terminator]
  │            │                     │              │
  │            │                     │              └── String terminator
  │            │                     └── Encoded dialogue text
  │            └── Metadata (NOT a lookup key)
  └── Stream marker (A9 = stream ID)
```

**Important**: The script prefix is NOT a lookup key. The same prefix value can appear with different text content at different locations. The game reads text inline at the current stream position.

### Stream Statistics (S100.STG Chunk 0)

| Stream ID | Dialogues | Example Offsets |
|-----------|-----------|-----------------|
| 0xA9 | 397 | 0xB4034, 0xB4056, 0xB4078... |
| 0xAA | ~200 | Various |
| 0xAB | ~150 | Various |
| 0x66 | ~50 | Various |

### Dialogue Types

There are three types of dialogues in STG files:

**1. Template-Associated Dialogues** (Text Region: 0xB4000-0xBC7FF)
- Have a 48-byte template block (0x8BF00123/0x8BF00145 signatures)
- Template contains speaker opcode, timing info, box parameters
- Dialogue text is located via `Ptr_A - 0x10` formula
- Captured by `scan_stg()` template-driven extraction

**2. Orphan Menu Texts** (Text Region: 0xB4000-0xBC7FF)
- `A9 00` marker texts WITHOUT associated templates
- Typically menu options, yes/no prompts, system messages
- Identified by `[br][opt]` pattern (real menus have options on separate lines)
- NOT captured by template scanning (no template pointer references them)
- Captured by `scan_stg()` orphan menu detection pass
- Context opcode: `0x00A9`

**3. Event Script Dialogues** (Event Script Region: 0xB0000-0xB4000)
- Embedded dialogues in the Event Script region
- Includes system prompts, item messages, story narration
- Identified by `A9 00` marker with strict validation:
  - Must have `[box:]` tag (dialogue structure), or
  - Must have kanji (real Japanese text), or
  - Must be a menu with `[br][opt]` pattern
- Context opcode: `0x00B0`

**4. Padding Region Dialogues** (Padding Region: 0xA0000-0xB0000) - NEW 2026-02-07
- Some chunks have dialogue data embedded in the padding region
- Same strict validation as Event Script region
- Context opcode: `0x00A0`
- Example: Chunk 4 in S100.STG has dialogues at 0xAE87C

**Statistics** (S100.STG):

| Type | Count | Region |
|------|-------|--------|
| Template-associated | 1,165 | 0xB4000-0xBC7FF |
| Orphan menus | 76 | 0xB4000-0xBC7FF |
| Event Script | 33 | 0xB0000-0xB4000 |
| Padding | 7 | 0xA0000-0xB0000 |
| **Total** | **1,281** | |

**Orphan Menu Categories** (S100.STG: 76 real menus, filtered from 97 raw texts):

| Category | Example | Count |
|----------|---------|-------|
| Tutorial menus | `[opt]操作の基本[br][opt]バトルの基本[br][opt]もういい` | 6 |
| Yes/No prompts | `この子供を連れて行きますか？[br][opt]はい[br][opt]いいえ` | 15 |
| System prompts | `スイッチがあります[br]ONにしてみますか？` | 42 |
| Navigation | `下り階段があります[br][opt]下る[br][opt]やめる` | 24 |
| Submarine controls | `どうする？[br][opt]停止[br][opt]浮上[br][opt]潜行[br][opt]進む` | 6 |
| Bounty board | `[box:system]名[opt]前[opt]ゴルザ...` | 4 |

Orphan menus are identified by context opcode `0x00A9` in the decoded output.

## Why Alternative Approaches Don't Work

### 1. MIPS Code Modification

**Investigation**: Searched MIPS code regions (0x77000-0x7FFFF, 0x80000-0x9FFFF) for address references to the text region.

**Findings**:
- Only 2 `LUI 0x8008` instructions found in entire code region
- No direct `LUI+ADDIU` patterns loading addresses in 0xB4000-0xBC7FF range
- MIPS code does NOT contain hardcoded text pointers

**Why it fails**: The dialogue system is event-driven, not address-driven. MIPS code calls the event script interpreter, which then reads from dialogue streams.

### 2. Script Prefix Redirection

**Investigation**: Analyzed whether changing the 2-byte script prefix could redirect to different dialogue content.

**Findings**:
- Same prefix value (e.g., `16 07`) appears with different text at different offsets
- Prefix is metadata (timing/display info), not a lookup key
- Game reads text inline at current stream position, not by prefix lookup

**Example showing prefix is NOT a lookup key**:
```
Offset 0xB4516: 16 07 "大きな街ね" 00
Offset 0xB5678: 16 07 "全く違う文章" 00   ← Same prefix, different text!
```

**Why it fails**: The prefix doesn't determine which text to display. Text is read sequentially from the stream position.

### 3. Text Relocation

**Investigation**: Analyzed whether dialogues could be moved to new locations with pointer updates.

**Findings**:
- Event script uses reference indices (0xA9, 0xAA), not byte offsets
- No pointer table mapping indices to text offsets was found
- Templates only cover ~15% of dialogues (173 out of 1,165 in S100)
- Non-template dialogues (85%) are embedded inline with no external references

**Why it fails**: The event script interpreter reads from sequential streams. There's no mechanism to redirect to arbitrary memory locations without reverse-engineering the entire interpreter.

### 4. Reflow Mode (Template Pointer Updates)

**Investigation**: Attempted to rebuild text region with variable-length translations and update template pointers.

**Findings**:
- Template Ptr_A at offset +6 points to dialogue text
- Updating pointers after text length changes caused:
  - Wrong scenes loading
  - Dialogues being skipped
  - Battle screens appearing instead of dialogue

**Why it fails**:
- Only 15% of dialogues have templates
- Game code has additional hardcoded references not in templates
- Event script region (0xB0000-0xB3FFF) has its own references that weren't updated

## Event Script System Deep Dive

### Event Script Region (0xB0000-0xB3FFF)

The event script region controls dialogue flow through command sequences:

```
Offset    Bytes                           Meaning
────────────────────────────────────────────────────────
0xB3B90   67 00 16 80 23 80 14 80        CMD 0x0067
          02 80 A9 00 BD 02              ref=A9, params

0xB3B9E   67 00 16 80 23 80 14 80        CMD 0x0067
          03 80 A9 00 BD 02              ref=A9, params

0xB3BAC   67 00 16 80 23 80 14 80        CMD 0x0067
          04 80 AA 00 6A 02              ref=AA, params
```

### 0x0067 Command Structure

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 2 | Command | 0x0067 (dialogue trigger) |
| 0x02 | 2 | Speaker 1 | Primary speaker opcode |
| 0x04 | 2 | Speaker 2 | Secondary speaker |
| 0x06 | 2 | Speaker 3 | Tertiary speaker |
| 0x08 | 2 | Context | Context opcode |
| 0x0A | 2 | Reference ID | Stream ID (0xA9, 0xAA, etc.) |
| 0x0C | 2 | Parameter | Additional flags |

### Execution Flow

```
1. Event script interpreter reaches 0x0067 command
2. Reads reference ID (e.g., 0xA9)
3. Gets current position in stream A9
4. Reads dialogue text at that position
5. Advances stream position past null terminator
6. Displays dialogue with speaker info
7. Continues to next event command
```

## Template vs Non-Template Dialogues

### Template Dialogues (~15%)

- Have 48-byte template blocks with signatures `0x8BF00123` and `0x8BF00145`
- Template contains Ptr_A pointing to text offset
- Can theoretically be relocated by updating Ptr_A
- **However**: Still part of sequential streams, so relocation breaks stream order

### Non-Template Dialogues (~85%)

- Embedded inline after `A9 00` (or similar) markers
- No external pointer references
- Read sequentially by event script interpreter
- **Cannot be relocated** without modifying event script interpreter

## Practical Implications

### For Translation

1. **Korean text must fit in original space**: Use shorter synonyms, abbreviations
2. **Truncation is unavoidable for some dialogues**: ~5-20% will be cut off
3. **Use `find_truncated.py`** to identify problematic dialogues before patching
4. **`[cursor]` tag does NOT help**: It adds 4 bytes, making text longer

### For Patching

1. **Only use fixed-length mode**: Reflow mode is broken
2. **Use `patch_all.py`**: Ensures unified character mapping across all files
3. **Preserve templates**: Do not modify the 48-byte template blocks
4. **Keep control codes**: `FF XX YY ZZ` sequences must be preserved

### Translation Tips for Long Dialogues

| Strategy | Example |
|----------|---------|
| Shorter synonyms | 하지만 → 근데, 그러나 → 허나 |
| Remove particles | 로말리아를 → 로말리아 |
| Abbreviate names | 로말리아 → RM (context-dependent) |
| Simplify grammar | ~하는 것이다 → ~한다 |

## Files Reference

| File | Purpose |
|------|---------|
| `python/patch_all.py` | Unified patcher (RECOMMENDED) |
| `python/find_truncated.py` | Find dialogues needing shortening |
| `python/patch_korean.py` | Single-file patcher (use with caution) |
| `translated/ko/S*_STG.txt` | Korean translation files |

## Future Research

If someone wants to enable variable-length translations, they would need to:

1. **Reverse-engineer the event script interpreter** in the main executable (SCPS_100.26)
2. **Understand the stream position tracking mechanism**
3. **Find where stream base addresses are stored** at runtime
4. **Potentially modify the main executable** to support a new lookup mechanism

This would require significant additional reverse-engineering effort and is beyond the scope of simple binary patching.

## See Also

- `STG_STRUCTURE.md` - Detailed chunk layout
- `STG_analysis.md` - File format overview
- `PATCHING.md` - Patching guide
- `TEXT_ENCODING.md` - Character encoding details
