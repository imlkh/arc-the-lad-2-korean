# STG File Structure - Arc the Lad 2

Complete reverse-engineering analysis of the STG (Stage) file format.

## File Overview

Each STG file contains multiple **chunks** of exactly **772,096 bytes (0xBC800)**.
Chunks represent individual scenes, stages, or cutscenes in the game.

| File | Chunks | Templates | Dialogues | Bare | Orphan Menus |
|------|--------|-----------|-----------|------|-------------|
| S100.STG | 11 | 1,195 | 1,313 | 25 | 75 |
| S200.STG | 18 | 1,787 | 1,990 | 26 | 119 |
| S300.STG | 5 | 320 | 392 | 0 | 66 |
| S400.STG | 11 | 783 | 882 | 5 | 65 |
| S500.STG | 8 | 534 | 683 | 4 | 72 |
| S600.STG | 10 | 754 | 921 | 0 | 90 |
| S700.STG | 33 | 2,613 | 3,146 | 14 | 269 |
| S800.STG | 15 | 1,056 | 1,390 | 0 | 118 |
| S900.STG | 13 | 945 | 1,223 | 2 | 126 |
| SA00.STG | 17 | 1,321 | 1,527 | 4 | 93 |
| SB00.STG | 11 | 790 | 911 | 13 | 61 |
| SC00.STG | 10 | 682 | 875 | 4 | 145 |
| SD00.STG | 9 | 688 | 941 | 18 | 128 |
| SE00.STG | 16 | 1,213 | 1,447 | 0 | 129 |
| SF00.STG | 25 | 2,517 | 3,363 | 17 | 342 |
| SG00.STG | 56 | 1,510 | 2,426 | 5 | 401 |
| SH00.STG | 1 | 49 | 738 | 0 | 239 |
| SI00.STG | 28 | 2,190 | 2,607 | 11 | 269 |
| SJ00.STG | 1 | 0 | 0 | 0 | 0 |
| **Total** | **298** | **20,947** | **26,775** | **148** | **2,807** |

**Note**: Dialogue counts include all types (template, bare, orphan menu, event script, padding).
Decoder quality: 0 garbage, 0 single-char fragments, 0 partial decodes.

## Chunk Layout (0xBC800 = 772,096 bytes)

```
┌─────────────────────────────────────────────────────────────┐
│ 0x00000 - 0x6FFFF: Graphics Data (458,752 bytes)           │
│   - 4-bit indexed (16 color) pixel data                    │
│   - Background tiles, character sprites, UI elements       │
│   - Approx. 14 frames at 256x256 or 56 frames at 128x128   │
├─────────────────────────────────────────────────────────────┤
│ 0x70000 - 0x76FFF: Sparse Data / Padding (28,672 bytes)    │
│   - ~85% zero bytes                                        │
│   - May contain additional metadata                        │
├─────────────────────────────────────────────────────────────┤
│ 0x77000 - 0x7FFFF: MIPS Code Region 1 (36,864 bytes)       │
│   - Scene-specific event scripts                           │
│   - Not present in all chunks (~82% zeros when empty)      │
├─────────────────────────────────────────────────────────────┤
│ 0x80000 - 0x9FFFF: MIPS Code Region 2 (131,072 bytes)      │
│   - Main game logic functions                              │
│   - Dialog system routines                                 │
│   - ~474 function calls (JAL instructions) per chunk       │
│   - ~19% zero bytes (dense code)                           │
├─────────────────────────────────────────────────────────────┤
│ 0xA0000 - 0xAFFFF: Padding (65,536 bytes)                  │
│   - ~98% zero bytes in most chunks                         │
│   - May contain embedded dialogue text in some chunks      │
│   - Used for VLUT + Korean text in patched files           │
├─────────────────────────────────────────────────────────────┤
│ 0xB0000 - 0xB3FFF: Event Script Region (16,384 bytes)      │
│   - ~89% sparse data (mostly zeros at start)               │
│   - Event script commands and dialogue triggers            │
│   - Active data typically starts around 0xB36F4+           │
├─────────────────────────────────────────────────────────────┤
│ 0xB4000 - 0xBC7FF: TEXT REGION (34,816 bytes)              │
│   - Dialog strings (null-terminated)                       │
│   - Event script templates (48 bytes each)                 │
│   - Script opcodes (10 bytes each, 0x2801 signature)       │
│   - Event trigger commands (14 bytes each, 0x0067 cmd)     │
│   - MIPS code fragments, data tables, null padding         │
│   - This is where translations are patched                 │
│   - See TEXT_REGION_BYTE_ANALYSIS.md for full type catalog  │
└─────────────────────────────────────────────────────────────┘
```

## Text Region Structure (0xB4000 - 0xBC7FF)

### Overview

The text region contains:
1. **Dialog Index** (first ~0x100 bytes): Scene header and metadata
2. **Dialog Strings**: Null-terminated text with control codes
3. **Event Script Templates**: 48-byte blocks marking dialog triggers

### Dialog String Format

```
[2-byte script prefix][text bytes][00 terminator]
```

Example:
```
16 07 こんにちは！ 00
└─┬─┘ └────┬────┘ └┘
Script  Text    Null
prefix        terminator
```

### Event Script Template (48 bytes)

Each template contains **two paired sub-blocks**:

```
Offset  Size  Field             Description
───────────────────────────────────────────────────────
BLOCK 1 (Primary - 0x23 signature)
0x00    4     Signature         0x8BF00123 (little-endian)
0x04    2     Speaker Opcode    See Speaker Opcodes table
0x06    2     Ptr_A             Dialog offset (Ptr_A - 0x10 = prefix)
0x08    2     Ptr_B             Text data region pointer (usually 0x0BF0)
0x0A    2     Ptr_C             Flags (0x0004 for primary)
0x0C    2     Unknown_1         Usually 0x8000
0x0E    2     Line Index        Dialog sequence number

BLOCK 2 (Secondary - 0x45 signature)
0x10    4     Signature         0x8BF00145 (little-endian)
0x14    2     Speaker Opcode    Same as primary
0x16    2     Ptr_A             Same as primary
0x18    2     Ptr_B             Same as primary
0x1A    2     Ptr_C             0x0000 (for secondary)
0x1C    2     Unknown_2         Usually 0x8000
0x1E    2     Line Index        Dialog sequence number

BOX CONTROL
0x20    2     Box Command       Usually 0x0063
0x22    2     Speaker Opcode    Mirrors main opcode
0x24    2     Timing Offset     Line timing/sequence
0x26    2     Box Type          Usually 0x002D

DISPLAY PARAMETERS
0x28    2     Box Height        0x0030 (48 pixels)
0x2A    2     Box Y Position    0x0062 (98 pixels from top)
0x2C    2     Dialog Flags      0x8002
0x2E    2     Animation ID      Variable (0x35, 0xA4, 0xA9, etc.)
```

### Speaker Opcodes

| Opcode | Speaker Type | Description |
|--------|--------------|-------------|
| 0x8005 | Player | Main character dialog |
| 0x8006 | NPC | Non-player character |
| 0x8009 | Party Member | Team member dialog |
| 0x800A | Shopkeeper | Shop/vendor interactions |
| 0x800D | Named NPC | Important named characters |
| 0x800E | Quest NPC | Quest-related NPCs |
| 0x8016 | Narrator | Story narration |
| 0x8018 | Tutorial | Tutorial messages |
| 0xFFFE | System | System messages (most common, ~74%) |

### Animation IDs

| ID | Occurrences | Possible Meaning |
|----|-------------|------------------|
| 0xA9 (169) | 88 | Standard dialog animation |
| 0xA4 (164) | 66 | Alternate dialog animation |
| 0x35 (53) | 9 | Quick dialog |
| 0x68 (104) | 2 | Extended animation |
| 0xC0 (192) | 2 | Special animation |

## Event Script Region (0xB0000 - 0xB3FFF)

The scene/event region contains structured event commands that control dialogue flow.

### Structure Overview

Most of this region is zero bytes at the beginning. Active event data typically starts around offset 0xB36F4 and contains:
1. **Embedded dialogue text** - System prompts, item messages, story text
2. **Event trigger commands** (starting around 0xB3B90)
3. **Speaker opcode sequences**

### Embedded Dialogues (NEW - 2026-02-07)

The Event Script region contains **embedded dialogue text** that is NOT covered by the main text region's template-based scanning. These include:

| Type | Example | Pattern |
|------|---------|---------|
| System prompts | スイッチがあります | `[box:system]...[box:close]` |
| Item messages | エルクは、「薬草」を手に入れた | Starts with character name + は |
| Story text | プロディアスの街が見える | Has kanji |
| Menu choices | もちろん！/ちょっと待った | Has `[br][opt]` |

**Detection**: The decoder scans for `A9 00` markers in this region with strict validation:
- Must have `[box:]` tag, or
- Must have kanji characters, or
- Must be a menu with `[br][opt]` pattern

**Statistics**:

| File | Event-Script Dialogues |
|------|------------------------|
| S100.STG | 33 |
| SG00.STG | 144 |

## Padding Region (0xA0000 - 0xAFFFF)

The padding region is primarily used for VLUT and Korean text storage in patched files, but some chunks also contain **embedded dialogue text** in the original game.

### Embedded Dialogues in Padding Region

Some chunks have dialogue data extending into the padding region. Example: S100.STG Chunk 4 has 7 dialogues at offset 0xAE87C.

**Detection**: Same as Event Script region - `A9 00` markers with strict validation.

**Context opcode**: `0x00A0` in decoder output.

**Statistics**:

| File | Padding Region Dialogues |
|------|--------------------------|
| S100.STG | 7 |
| SG00.STG | 26 |

### VLUT Placement Considerations

When placing VLUT for variable-length patching, the patcher must avoid overwriting dialogue data:

- S100 Chunk 4: Dialogues at 0xAE87C, VLUT placed at 0xA9500 (safe - 21KB gap)
- Check for data regions before placing VLUT

### Event Trigger Command (0x0067)

The 0x0067 command appears to trigger dialogue display:

```
Offset  Size  Field             Description
──────────────────────────────────────────────────
0x00    2     Command           0x0067 (little-endian)
0x02    2     Speaker 1         Speaker opcode (e.g., 0x8016)
0x04    2     Speaker 2         Additional speaker (e.g., 0x8023)
0x06    2     Speaker 3         Additional speaker (e.g., 0x8014)
0x08    2     Speaker 4         Context opcode (e.g., 0x8002)
0x0A    2     Reference ID      Index value (0x00A9, 0x00AA, etc.)
0x0C    2     Unknown           Additional parameter
```

Example sequence from S100.STG at 0xB3B90:
```
67 00 16 80 23 80 14 80 02 80 A9 00 BD 02   CMD 0x0067, speakers, ref 0xA9
67 00 16 80 23 80 14 80 03 80 A9 00 BD 02   CMD 0x0067, speakers, ref 0xA9
67 00 16 80 23 80 14 80 04 80 AA 00 6A 02   CMD 0x0067, speakers, ref 0xAA
```

### Why Dialogue Relocation is Difficult

Analysis of the event script region reveals why relocating dialogues is complex:

1. **No Simple Offset Pointers**: The MIPS code in STG files (0x80000-0x9FFFF) does not contain direct LUI+ADDIU address loads pointing to the text region
2. **Index-Based Lookup**: The reference IDs (0xA9, 0xAA, etc.) appear to be indices into a lookup mechanism, not direct byte offsets
3. **Event-Driven System**: Dialogues are triggered by the event script engine, not by hardcoded MIPS addresses

This means modifying dialogue offsets requires understanding the full event script interpreter, which is beyond simple binary patching.

## MIPS R3000 Code Regions

The STG files contain embedded MIPS R3000A CPU code (PlayStation's processor).

### Code Region 1 (0x77000 - 0x7FFFF)
- Scene-specific event handlers
- Not always present (sparse in many chunks)

### Code Region 2 (0x80000 - 0x9FFFF)
- Main game logic
- Dialog display routines
- ~474 JAL (Jump And Link) function calls per chunk

### Identifying MIPS Code

Function prologues:
```assembly
addiu $sp, $sp, -N    ; E8FF BD27 (N=24) or F8FF BD27 (N=8)
sw    $ra, offset($sp) ; AF BF XX XX
```

Function epilogues:
```assembly
lw    $ra, offset($sp) ; 8F BF XX XX
addiu $sp, $sp, N
jr    $ra              ; 03 E0 00 08
```

## Graphics Data Format

The graphics region (0x00000 - 0x6FFFF) uses:
- **4-bit indexed color** (16 colors per palette)
- Each byte = 2 pixels (high nibble, low nibble)
- Total: 458,752 bytes = 917,504 pixels

Possible configurations:
- 14 frames at 256x256 pixels
- 56 frames at 128x128 pixels
- Mixed tile sizes for UI elements

## Patching Considerations

When patching Korean translations:

1. **Text Region**: Primary text at 0xB4000 - 0xBC7FF
2. **Padding Region**: VLUT + Korean overflow text at 0xA0000 - 0xAFFFF
3. **Template Preservation**: Do not modify the 48-byte templates
4. **Control Codes**: Preserve all `FF XX YY ZZ` control sequences
5. **Null Terminators**: Every dialog must end with 0x00
6. **Variable-Length VLUT**: Chunks with VLUT allow Korean text to exceed original byte count by storing overflow in padding region. Master pointer at chunk+0xAFF00.
7. **Fixed-Length Fallback**: Chunks without VLUT require Korean text to fit within original byte count (safe truncation applied)

## See Also

- `DIALOGUE_SYSTEM_ANALYSIS.md` - Complete dialogue system reverse-engineering
- `TEXT_REGION_BYTE_ANALYSIS.md` - 7 byte sequence types in text region
- `DECODER_FIXES.md` - Decoder garbage filter rules and structural detection
- `TEXT_ENCODING.md` - Character encoding and control codes
- `COMM_IMG_chars.md` - Font character table
- `PATCHING_KOREAN.md` - Patching workflow
