# COMM.DAT Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `COMM.DAT` |
| Size | 67,584 bytes (66.0 KB, 0x10800) |
| Sectors | 33 CD-ROM sectors (2,048 bytes each) |
| Type | PS1 MIPS executable overlay -- battle animation/command module |
| Load address | RAM `0x80010000` |
| GP register | `0x80018058` (BSS base) |
| Contains text | **No** -- code + battle data + palettes + sprite commands |

## Verdict: No Translatable Text

COMM.DAT is a **battle animation/command module** -- a PS1 MIPS overlay loaded at `0x80010000` (distinct from the `0x80026000` UI overlays). It contains executable code, character battle animation data, color palettes, and GPU sprite rendering commands. There are **0 text strings** of any kind. "COMM" in this context stands for "common" or "command" (battle commands), not "communication" or "font."

## Purpose

COMM.DAT manages battle system visuals:
- Character/enemy battle sprite animation definitions
- Per-character animation data blocks (22 playable characters/entities)
- Color palettes (CLUTs) for battle sprites
- GPU display list commands for sprite rendering
- Animation frame sequencing and timing

The module is loaded at `0x80010000`, a different RAM region from the UI overlays (`0x80026000`). This means it can coexist with any of the UI modules (SDIC.BIN, YGUILD.BIN, YSHOP.BIN, etc.) in memory simultaneously.

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x00047` | 72 bytes | **MIPS Bootstrap** | Function prologue, JAL to init, GP register setup |
| `0x00048`-`0x000A7` | 96 bytes | **Character Pointer Table** | 22 x 4-byte RAM pointers + 3 BSS pointers |
| `0x000AC`-`0x00407` | 860 bytes | **Animation Group Table** | 33 groups x 6 identical RAM pointers |
| `0x00408`-`0x0804F` | ~31 KB | **Battle Animation Data** | 12-byte records per character (self-referencing offset tree) |
| `0x08050`-`0x087FF` | ~1.9 KB | **BSS Region** | Zero-filled runtime variable storage |
| `0x08800`-`0x08FFF` | 2,048 bytes | **CLUT Palettes** | ~49 PS1 15-bit RGB palettes (32 bytes each) |
| `0x09000`-`0x105D9` | ~30 KB | **Sprite/Animation Commands** | 8-byte GPU primitives, 0xFFFF delimited |
| `0x105DA`-`0x107FF` | 550 bytes | **Padding** | Zero-filled to CD-ROM sector boundary |

### Shannon Entropy

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | 6.17 bits/byte | Moderate-high (mixed code + structured data) |
| Bootstrap code (0x0000) | 5.82 bits/byte | Typical for MIPS code |
| Animation data (0x0408+) | 5.5-6.5 bits/byte | Structured binary data |
| Palettes (0x8800) | 5.36 bits/byte | Color data with gradients |
| Sprite commands (0x9000+) | 5.8-6.5 bits/byte | GPU command data |

## MIPS Bootstrap (0x00000 - 0x00047)

The file begins with a small MIPS bootstrap function and GP setup:

```
0x0000: ADDIU SP, SP, -24        ; function prologue
0x0004: SW    RA, 20(SP)         ; save return address
0x0008: SW    FP, 16(SP)         ; save frame pointer
0x000C: MOVE  FP, SP
0x0010: JAL   0x80010030         ; call init (trivial: JR RA at 0x0030)
0x0014: NOP
0x0018: MOVE  SP, FP
0x001C: LW    RA, 20(SP)
0x0020: LW    FP, 16(SP)
0x0024: ADDIU SP, SP, 24
0x0028: JR    RA                 ; return
0x002C: NOP
0x0030: JR    RA                 ; init stub (no-op)
0x0034: NOP
0x0038: LUI   GP, 0x8002         ; set up global pointer
0x003C: ADDIU GP, GP, -0x7FA8    ; GP = 0x80018058
0x0040: J     0x80010000         ; jump to start
0x0044: NOP
```

The bootstrap is minimal -- it sets up the GP register (pointing to the BSS region at file offset `0x8058`) and returns immediately. The actual animation logic is likely driven by function pointers called from SCPS_100.26's battle engine.

## Character Pointer Table (0x0048 - 0x00A7)

22 RAM pointers to character-specific animation data blocks, plus 3 BSS runtime pointers:

| Index | RAM Address | File Offset | Block Size | Character |
|-------|------------|-------------|------------|-----------|
| 0 | `0x80010408` | `0x0408` | 480 B | Character 0 |
| 1 | `0x800105E8` | `0x05E8` | 588 B | Character 1 |
| 2 | `0x80010834` | `0x0834` | 600 B | Character 2 |
| 3 | `0x80010A8C` | `0x0A8C` | 600 B | Character 3 |
| ... | ... | ... | ... | ... |
| 21 | `0x800134BC` | `0x34BC` | 576 B | Character 21 |
| 22 | `0x80018058` | `0x8058` | -- | BSS: runtime state A |
| 23 | `0x80018064` | `0x8064` | -- | BSS: runtime state B |
| 24 | `0x80018070` | `0x8070` | -- | BSS: runtime state C |

The 22 character entries correspond to the game's playable characters and possibly key enemy types. Block sizes range from 480 to 600 bytes (40-50 records of 12 bytes each).

## Animation Group Table (0x00AC - 0x00407)

33 groups of 6 identical RAM pointers each (6 x 4 bytes = 24 bytes per group). The "6 identical pointers" pattern suggests 6 directional views or 6 battle formation slots per animation group.

## Battle Animation Data (0x0408 - 0x804F)

### Record Format

Each data block contains 12-byte records:

```
struct AnimRecord {     // 12 bytes
    uint16_t offset_a;  // Self-referencing file offset
    uint16_t offset_b;  // Self-referencing file offset
    uint16_t offset_c;  // Self-referencing file offset
    uint16_t param_a;   // Animation parameter
    uint16_t param_b;   // Animation parameter
    uint16_t param_c;   // Animation parameter
};
```

- The first 3 fields are **16-bit file offsets** (range 0x0020-0x35E5) pointing to other records within the data block region -- forming a self-referencing tree structure for animation state machines
- The second 3 fields are parameters controlling animation IDs, palette references, or frame timing
- The grouping of 3 suggests 3 animation variants (e.g., attack, defend, idle)

## CLUT Palettes (0x8800 - 0x8FFF)

~49 PS1 color palettes, 32 bytes each (16 colors x 16-bit RGB555):

| Bit Layout | Description |
|-----------|-------------|
| Bits 0-4 | Red (0-31) |
| Bits 5-9 | Green (0-31) |
| Bits 10-14 | Blue (0-31) |
| Bit 15 | Semi-Transparency Processing flag |

Every palette starts with color 0 = `0x0000` (transparent black per PSX SPX). Common patterns include:
- Smooth dark-to-light gradients (skin tones, armor materials)
- High-saturation accent colors at specific indices
- Index 2 consistently uses bright blue `(0,0,232)` across multiple palettes (selection highlight?)

These palettes are uploaded to VRAM alongside the COMM.IMG texture data and used by the battle sprite renderer to colorize the 4bpp sprite graphics.

## Sprite/Animation Commands (0x9000 - 0x105D9)

Variable-length GPU rendering command sequences, delimited by `0xFFFF`:

| Property | Value |
|----------|-------|
| Total `0xFFFF` delimiters | ~1,539 |
| Dominant record size | 8 bytes |
| Region size | ~30 KB |

### 8-Byte Command Format

```
struct SpriteCmd {      // 8 bytes
    int16_t  x_pos;     // X position/coordinate
    int16_t  y_pos;     // Y position/UV coordinate
    int16_t  offset;    // Displacement or source offset
    uint8_t  cmd_type;  // Draw command (0x11, 0x12, 0x22, 0x23, 0x33, 0x44)
    uint8_t  frame_idx; // Frame/timing index (0x04-0x0B)
};
```

These commands define how individual sprite tiles are composed into full character animations on screen, specifying position, texture source, and rendering mode for each frame.

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **COMM.IMG** | Font/sprite texture atlas -- COMM.DAT's palette and sprite commands reference graphics stored in COMM.IMG |
| **COMM.SND** | Common sound bank -- loaded alongside COMM.DAT for battle audio |
| **CHA.BIN** | Character sprite archive -- separate from COMM.DAT's animation definitions |
| **SCPS_100.26** | Main executable -- drives the battle engine that calls COMM.DAT's animation functions |

## Relevance to Korean Translation

**COMM.DAT does not need to be modified for text translation.** It contains no text, character mappings, or font metrics. It is a battle animation/rendering module that operates on graphical data.

The earlier hypothesis in `COMM_IMG_analysis.md` that COMM.DAT might be a "character mapping table / font metrics" file is **incorrect**. The Shift-JIS-to-charID mapping tables are actually located in SCPS_100.26 at file offset `0xBE534` (RAM `0x8017F134`), as documented in `TEXT_ENCODING.md`.
