# CHA.BIN Sprite Archive Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `CHA.BIN` |
| Size | 4,085,760 bytes (3,990 KB / 3.90 MB) |
| Date | Nov 7, 1996 |
| Type | Uncompressed character sprite archive |
| Contains text | **No** — purely graphical data |

## Verdict: No Translatable Text

CHA.BIN contains exclusively graphical data: character sprites, color palettes, and animation tables. The text decoder found **0 real strings**. All 76,022 "strings" detected by full scan are false positives — 4bpp pixel data bytes that coincidentally map to valid character IDs. The 543 `FF 08` byte patterns are coincidental occurrences in pixel data, not dialogue markers.

## Data Composition

| Metric | Value |
|--------|-------|
| Null bytes (0x00) | 33.9% (transparent pixels) |
| Non-null bytes | 66.1% (sprite/animation data) |
| Shannon entropy | 5.59 bits/byte |
| Sprite data | 3,844 KB (94.9% utilization) |
| Zero padding | ~205 KB (5.1%) |
| Block alignment | 0x800 (2,048 bytes = PS1 CD-ROM sector) |

### Byte Frequency (Top 10)

| Byte | Count | Percentage | Likely meaning |
|------|-------|------------|----------------|
| 0x00 | 1,384,587 | 33.89% | Transparent pixels (palette index 0) |
| 0x01 | 248,357 | 6.08% | Palette index 1 (outline/shadow) |
| 0xFF | 114,413 | 2.80% | Animation terminators / palette indices 15+15 |
| 0x80 | 91,528 | 2.24% | Display list command prefix |
| 0x11 | 67,374 | 1.65% | Packed pixels: index 1 + index 1 |
| 0x02 | 61,662 | 1.51% | Palette index 2 |
| 0x10 | 51,876 | 1.27% | Packed pixels: index 0 + index 1 |
| 0x88 | 50,586 | 1.24% | Packed pixels: index 8 + index 8 |
| 0x08 | 44,769 | 1.10% | Display list sub-command / palette index 8 |
| 0x09 | 33,324 | 0.82% | Packed pixels: index 9 + index 0 |

### 4bpp Confirmation (Nibble Analysis)

| Nibble | Index 0 frequency | Interpretation |
|--------|-------------------|----------------|
| High nibble | 49.2% | Right pixel = transparent |
| Low nibble | 42.6% | Left pixel = transparent |

Nearly half of all nibbles are palette index 0 (transparent), exactly matching character sprites with transparent backgrounds. This definitively confirms the file stores 4bpp (16-color) indexed pixel data.

## Archive Structure

### Sprite Entries

The archive contains **246 sprite entries**, each beginning with a multi-CLUT header on a 0x800-aligned boundary.

| Property | Value |
|----------|-------|
| Total entries | 246 |
| Min entry size | 0.2 KB |
| Max entry size | 70.0 KB |
| Average entry size | 15.6 KB |
| Alignment | 0x800 (PS1 CD-ROM sector) |

There is **no index table** at the start of the file. Entry offsets are likely hardcoded in `SCPS_100.26` (the main game executable).

### Entry Internal Layout

Each sprite entry follows this general structure (sizes vary per character):

| Offset | Size | Contents |
|--------|------|----------|
| +0x0000 | 32 bytes | **CLUT 0** — Primary 16-color palette |
| +0x0020 | 32 bytes | **CLUT 1** — Secondary palette (transparent fill or alternate) |
| +0x0040 | 32 bytes | **CLUT 2** — Alternate palette (costume/damage variant) |
| +0x0060 | 32 bytes | **CLUT 3** — Effect palette (magic/special) |
| +0x0080 | ~14-56 KB | **4bpp pixel data** — Packed nibbles, 2 pixels per byte |
| varies | ~2-4 KB | **Display list commands** — GPU rendering instructions |
| varies | ~4-26 KB | **Animation frame tables** — Frame indices, coordinates, timing |
| varies | 0-16 KB | **Zero padding** — Alignment to next 0x800 boundary |

### CLUT (Color Lookup Table) Format

Each CLUT is 32 bytes = 16 entries of 16-bit PS1 RGB555 colors. Per PSX SPX, 4bpp CLUTs are stored in VRAM as 16×1 pixel images. CLUT X positions must be multiples of 16 halfwords; Y can be any row 0-511.

```
Bit layout: 0BBBBBGGGGGRRRRR (little-endian)
  Bits 0-4:   Red (0-31)
  Bits 5-9:   Green (0-31)
  Bits 10-14: Blue (0-31)
  Bit 15:     Semi-transparency processing (STP) flag
```

Key palette values observed:

| Value | RGB | Meaning |
|-------|-----|---------|
| 0x0000 | R=0, G=0, B=0 | Fully transparent (per PSX SPX: color 0000h = transparent in textured primitives) |
| 0x7C1F | R=31, G=0, B=31 | Magenta — transparent key color |
| 0x18A5 | R=5, G=5, B=6 | Dark gray — shared base color for main characters |
| 0x7FFF | R=31, G=31, B=31 | White — common in bright/effect sprites |
| 0x739C | R=28, G=28, B=28 | Light gray — highlight color |

**Note on transparency:** Per PSX SPX, color value 0x0000 is always rendered as fully transparent regardless of the STP bit. True black (R=0, G=0, B=0) cannot be displayed in textured primitives — the game likely uses 0x8000 (STP=1, RGB=0,0,0) or a near-black value instead where opaque black is needed.

### Display List Commands

Sprite rendering uses PS1 GPU display list primitives found in the animation region:

| Command | Count (entry 0) | Description |
|---------|-----------------|-------------|
| `80 08` | 423 | Sprite tile reference |
| `80 10` | 370 | Sprite tile (alternate) |
| `00 11` | 370 | Frame coordinate entry |
| `80 11` | 195 | Extended frame entry |
| `02 11` | 127 | Frame variant |
| `80 18` | 97 | Multi-tile composite |
| `FF FF` | 646 | Animation sequence terminator |

### Animation Frame Tables

Frame lists use `01 XX` references (where XX = frame index) terminated by `01 00 FF FF`. Entry 0 alone contains 1,585 frame reference pairs, indicating complex multi-frame character animations (idle, walk, attack, magic, hit, death, etc.).

## Main Character Entries (0x18A5 Base Palette)

Six entries share the `0x18A5` dark gray base color, likely corresponding to main playable characters or their alternate costumes:

| # | Offset | Size | Notes |
|---|--------|------|-------|
| 0 | 0x000000 | 20.0 KB | First character (3 CLUTs) |
| 5 | 0x011800 | 22.0 KB | Second character (4 CLUTs) |
| 9 | 0x023000 | 51.4 KB | Large character (3 CLUTs) |
| 18 | 0x057800 | 18.0 KB | Fourth character (4 CLUTs) |
| 24 | 0x069000 | 60.0 KB | Large character (3 CLUTs) |
| 142 | 0x230000 | 16.0 KB | Palette bank / alternate costumes (4 CLUTs) |

## Section Map (69 Data Sections)

The file is divided into 69 non-zero data sections separated by 256+ byte zero-padded gaps. Selected major sections:

| Section | Offset Range | Size | Content |
|---------|-------------|------|---------|
| 0 | 0x000000-0x00B596 | 45.4 KB | First character group |
| 2 | 0x00F88A-0x020B7F | 68.7 KB | Character with full animation set |
| 4 | 0x030807-0x052C90 | 137.1 KB | Large multi-character block |
| 9 | 0x08801B-0x098AA6 | 66.6 KB | Character with 4 palette variants |
| 32 | 0x08D800-0x09D7FF | 63.9 KB | Full character entry |

## Relevance to Korean Translation

**CHA.BIN does not need to be modified for text translation.** It contains only graphical sprite data.

However, if visual modifications are desired (e.g., character name labels rendered as sprites), the palette and pixel data structures documented above would be relevant. The 4bpp bitplane format is the same as the font in `COMM.IMG`, so the same extraction/injection tools could be adapted.
