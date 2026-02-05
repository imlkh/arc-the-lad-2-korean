# YEND.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `YEND.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay -- ending credits controller |
| Load address | RAM `0x80026000` |
| Active data | 12,364 bytes (12.1% of file) |
| BSS region | 90,036 bytes (87.9% of file) |
| Contains text | **Yes** -- 155 ASCII credit strings (staff names, section headers) |

## Verdict: Translatable Text (ASCII Credits)

YEND.BIN is the **Ending Credits Module** -- a dynamically-loaded PS1 MIPS overlay that controls the end-game staff credits sequence. Unlike other text-bearing overlays (SDIC.BIN, YGUILD.BIN, SMITH.BIN) which use the game's custom text encoding, YEND.BIN stores its credits as **plain ASCII strings** with a custom 80-byte character lookup table. The credits are entirely in romanized Japanese (no kanji/kana).

## Purpose

YEND.BIN implements the **ending credits scroll** displayed after completing the game. It manages:
- Two display modes: **paged screens** (key staff shown as grouped pages) and **scrolling text** (remaining credits scroll vertically)
- A transition sequence with special effects between the two modes
- Character rendering using a custom ASCII-to-font lookup table
- 214 credit display entries organized in a structured table

The module is loaded at `0x80026000`, the same address used by SDIC.BIN, YGUILD.BIN, YSHOP.BIN, YPROP.BIN, and YSEG.BIN. Only one of these six overlays can be loaded at a time.

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0B23` | 2,852 bytes | **Credit Strings** | 155 null-terminated ASCII strings (4-byte aligned) |
| `0x0B24`-`0x0B27` | 4 bytes | **Padding** | Zero alignment |
| `0x0B28`-`0x0B6B` | 68 bytes | **Function Dispatch Table** | 17 x 4-byte RAM pointers to code handlers |
| `0x0B6C`-`0x0B6F` | 4 bytes | **Padding** | Zero separator |
| `0x0B70`-`0x0C47` | 216 bytes | **Jump Table** | 54 x 4-byte RAM pointers (switch-case for entry types) |
| `0x0C48`-`0x229F` | 5,720 bytes (5.6 KB) | **MIPS Code** | ~34 functions (credit display logic) |
| `0x22A0`-`0x2FFB` | 3,420 bytes | **Credit Display Struct Table** | 214 x 16-byte entries controlling credit layout |
| `0x2FFC`-`0x304B` | 80 bytes | **Character Encoding Lookup** | ASCII character mapping table |
| `0x304C`-`0x18FFF` | 90,036 bytes (87.9 KB) | **BSS Region** | Runtime variable storage (zero-filled in file) |

### Shannon Entropy

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | ~1.0 bits/byte | Very low (88% null bytes from BSS) |
| Credit Strings | ~4.8 bits/byte | Typical for ASCII text with padding |
| MIPS Code | ~5.4 bits/byte | Typical for compiled MIPS code |
| Struct Table | ~2.5 bits/byte | Low -- structured data with many repeated patterns |

## Credit Strings (0x00000 - 0x0B23)

### Overview

| Property | Value |
|----------|-------|
| Total strings | 155 |
| Encoding | Plain ASCII (0x20-0x7E), null-terminated, 4-byte aligned |
| Region size | 2,852 bytes |
| First string | `0x0000`: " Yukihiro Kawano" |
| Last string | `0x0B18`: "Producer:" |

The strings are stored in **reverse display order** -- the last credits to appear on screen (Producer, Director) are at the end of the string region, while Thank You names are at the start. The struct table references these strings via RAM pointers.

### Content Categories

| Category | Count | Examples |
|----------|-------|---------|
| Section headers | 18 | "Producer:", "Director:", "Programmer:", "Graphic:", etc. |
| Staff names | 124 | " Ryoji Akagawa(SCEI)", " Toshirou Tsuchida(G-CRAFT)" |
| Character/voice pairs | 24 | "ELC" + " Ai Orikasa", "ARC" + " Hekiru Shiina" |
| Song info | 2 | "Song Title: Musicman", " by Cara Jones(SHANTE)" |

Most name strings begin with a leading space (" ") for visual indentation in the credits display.

### Full Credit Listing

#### Key Staff
| Role | Name |
|------|------|
| **Producer** | Ryoji Akagawa (SCEI) |
| **Director** | Toshirou Tsuchida (G-CRAFT) |
| **Programmer** | Satoshi Tetsuka, Norihiko Yonesaka, Kou Satou (G-CRAFT) |
| **A.Director** | Chikara Yanagimachi, Masato Shimajiri, Katsutoshi Yamamoto (G-CRAFT) |
| **Character Design** | Seiji Toyokura, Yoshito Abe, Reiko Nagashima, Megumi Nakamura, Shinichi Mochizuki |
| **World Design** | Ryuichi Kunisue |
| **CG Movie** | Masayoshi Obata, Takeshi Gouya |
| **Sound Producer** | Takahumi Hujisawa (SCEI), Tomohiko Hukuoka |
| **Composer** | Masahiro Ando (T-SQUARE) |
| **Executive Producer** | Yukio Nagasaki (SCEI), Toshiyuki Miyata (SCEI) |

#### Voice Cast
| Character | Voice Actor |
|-----------|------------|
| ELC (エルク) | Ai Orikasa |
| LIEZA (リーザ) | Yoko Asada |
| SHU (シュウ) | Syuuichi Ikeda |
| SHANTE (シャンテ) | Michiko Neya |
| DIECBECK (ヂークベック) | Toranori Yoshikawa |
| GRUGA (グルガ) | Takashi Nagasako |
| SANIA (サニア) | Hekiru Shiina |
| ARC (アーク) | Hiro Yuuki |
| KUKURU (ククル) | Konami Yoshida |
| POCO (ポコ) | Chika Sakamoto |
| TOSH (トッシュ) | Nobuyuki Hiyama |
| IGA (イーガ) | Kiyoyuki Yanada |
| GOGEN (ゴーゲン) | Masato Tujimura |
| CHONGARA (チョンガラ) | Kenichi Ogata |

#### Song
- **Title**: "Musicman" by Cara Jones (SHANTE)

## Function Dispatch Table (0x0B28 - 0x0B6B)

17 RAM pointers to code handler functions within the MIPS code region:

| Index | RAM Address | File Offset | Likely Purpose |
|-------|------------|-------------|----------------|
| 0 | `0x80026EB4` | `0x0EB4` | Display mode handler A |
| 1 | `0x80026E9C` | `0x0E9C` | Display mode handler B |
| 2 | `0x80026ECC` | `0x0ECC` | Page transition handler |
| 3 | `0x80026EDC` | `0x0EDC` | Text renderer |
| 4 | `0x80026EFC` | `0x0EFC` | Scroll controller |
| 5-8 | `0x80026F38`-`0x80026F68` | `0x0F38`-`0x0F68` | Animation/timing handlers |
| 9-12 | `0x80026F7C`-`0x80026FC4` | `0x0F7C`-`0x0FC4` | State machine phases |
| 13-14 | `0x80026FC4`-`0x80026FD4` | `0x0FC4`-`0x0FD4` | Cleanup handlers |
| 15-16 | `0x80026FF4`-`0x80027008` | `0x0FF4`-`0x1008` | Final sequence handlers |

## Jump Table (0x0B70 - 0x0C47)

54-entry jump table used for switch-case dispatching based on credit entry type. Only 4 unique targets:

| RAM Address | File Offset | Occurrences | Likely Function |
|------------|-------------|-------------|-----------------|
| `0x8002743C` | `0x143C` | 7x | Return type 1 (text display) |
| `0x80027448` | `0x1448` | 6x | Return type 2 (section header) |
| `0x80027454` | `0x1454` | 2x | Return type 3 (special entry) |
| `0x80027460` | `0x1460` | 39x | Default handler (null/spacer) |

The dominance of the default handler (39 of 54 entries) indicates most entry types fall through to a no-op, with active display only for specific type codes.

## MIPS Code Region (0x0C48 - 0x229F)

### Function Summary

| Metric | Value |
|--------|-------|
| Total functions | ~34 (31 with stack frame prologues) |
| Code size | 5,720 bytes (5.6 KB) |
| Internal JAL targets | 16 unique addresses |
| External JAL targets | 26 unique addresses (all in SCPS_100.26) |
| ADDIU SP,SP (prologues/epilogues) | 62 (31 matched pairs) |
| JR RA (returns) | 34 |

### External Dependencies (SCPS_100.26)

| RAM Address | Call Count | Likely Purpose |
|------------|-----------|----------------|
| `0x800F5C30` | 11x | Sprite/text rendering primitive |
| `0x8013BEA8` | 7x | GPU display list / DMA submit |
| `0x800F7330` | 7x | Color/palette setup |
| `0x800C2EB4` | 5x | Timing/frame sync |
| `0x8010372C` | 5x | Screen clear/fill |
| `0x800CF7C8` | 4x | Menu/panel draw utility |
| `0x800F6B58` | 4x | Sprite positioning |
| `0x800C3254` | 3x | Text rendering / string display |
| `0x800C327C` | 3x | Text rendering variant |
| `0x800F4DF4` | 3x | Graphics primitive |
| `0x800F54C0` | 3x | GPU command |
| `0x80103AA0` | 3x | Screen transition effect |
| `0x801017FC` | 3x | Fade/blend effect |

The most-called function (`0x800F5C30`, 11x) is likely a general-purpose sprite or text rendering primitive. The heavy use of graphics functions (`0x800F*` range, 33 total calls) reflects the credits module's focus on visual presentation.

### LUI References (RAM Address Bases)

| Base Address | Count | Purpose |
|-------------|-------|---------|
| `0x801A0000` | 34x | Game state / animation variables |
| `0x801B0000` | 19x | Display list / rendering buffers |
| `0x80030000` | 18x | BSS region (runtime variables within this module) |
| `0x80020000` | 16x | Module data (string pointers, struct table) |
| `0x800D0000` | 4x | SCPS_100.26 functions |
| `0x801F0000` | 4x | Shared game state flags |

## Credit Display Struct Table (0x22A0 - 0x2FFB)

### Overview

214 entries, each 16 bytes:

```c
struct CreditEntry {     // 16 bytes
    uint32_t type;       // Entry type code
    uint32_t y_pos;      // Y screen position (or timing parameter)
    uint32_t str_ptr;    // RAM pointer to string (0x80026xxx) or NULL
    uint32_t style;      // Display style / rendering mode
};
```

### Entry Types

| Type Code | Meaning | Count | Description |
|-----------|---------|-------|-------------|
| `0x10` | Text entry | 147 | Display a credit string at position (y_pos, centered) |
| `0xE0` | Page separator / spacer | 18 | Marks page boundaries (paged mode) or visual gaps |
| `0x180` | Scroll section break | 10 | Timing gap between scrolling credit groups |
| `0x30` | Short pause | 2 | Brief delay in scroll |
| `0x60` | Effect trigger | 1 | Triggers visual effect during transition |
| `0x78` | Timing control | 2 | Frame-based timing parameter |
| `0x01` | State change | 1 | Mode transition marker |
| `0xA4` | Position marker | 1 | Absolute positioning (y=132) |
| `0x258` | Long delay | 1 | Extended pause (600 frames?) |
| `0x438` | Very long delay | 1 | Very extended pause (1080 frames?) |
| `0x644` | Extended timing | 1 | Special timing (1604 frames?) |
| `0x12C` | Medium delay | 1 | 300-frame pause |
| Other | Control entries | ~28 | Zero-type entries with various style codes |

### Display Styles

| Style | Meaning | Usage |
|-------|---------|-------|
| 2 | Last entry in group | Applied to the final name in each credit section |
| 4 | Section header | Applied to role labels ("Producer:", "Graphic:", etc.) |
| 5 | Scrolling text | Applied to entries in the vertical scroll portion |
| 6-16 | Special effects | Various visual transition effects during mode changes |

### Two Display Modes

**Mode 1: Paged Screens (entries 0-76)**
- Credits display as grouped pages, each containing a section header and 2-4 names
- Y positions are 32, 50, 68, 86, 104 (18-pixel spacing)
- `0xE0` spacer entries separate pages
- Covers key staff: Producer, Director, Programmer, A.Director, Graphic, Character Design, World Design, CG Movie, Sound

**Transition (entries 77-86)**
- Special effect entries (types 0x01, 0x60, 0x78, 0x644) trigger the visual transition from paged to scrolling mode

**Mode 2: Vertical Scroll (entries 87-197)**
- Credits scroll upward from y=240 (bottom of screen)
- `0x180` entries create pauses between groups
- Covers: A.Producer, Graphic (detailed), London Recording, Jacket & Booklet, Promotion, Voice Cast, Song, Debug Team, Co Producer, Executive Producer, Special Thanks

**Epilogue (entries 198-213)**
- Final timing and effect entries for the credits conclusion

### Credit Page Structure (Mode 1)

Each page follows this pattern:
```
[0xE0] SPACER (page break, style=4)
[0x10] y=32  Section header (e.g., "Producer:")     style=4
[0x10] y=50  First name                              style=4
[0x10] y=68  Second name                             style=4
[0x10] y=86  Third name (last in group)              style=2
```

Style=2 on the last entry signals the display engine to hold the page, then transition to the next page.

### Credit Scroll Structure (Mode 2)

Each scroll group follows this pattern:
```
[0x180] SCROLL BREAK (timing gap)
[0x10] y=240  Section header                         style=5
[0x10] y=240  Name 1                                 style=5
[0x10] y=240  Name 2                                 style=5
...
[0x10] y=240  Last name                              style=2
```

All scroll entries use y=240 (bottom of PS1 screen). The scroll engine renders each entry at the bottom and scrolls everything upward. Style=2 on the last entry may trigger a brief pause before the next group.

## Character Encoding Lookup Table (0x2FFC - 0x304B)

An 80-byte table mapping internal character indices to ASCII values. The credits use a custom encoding where each byte in the credit strings is an **index into this table**, not a direct ASCII value. This is different from the game's main text encoding (described in `TEXT_ENCODING.md`).

| Index Range | ASCII Output | Count |
|-------------|-------------|-------|
| 0 | Space (0x20) | 1 |
| 1-26 | A-Z | 26 |
| 27-30 | Space (padding) | 4 |
| 31-56 | a-z | 26 |
| 57-59 | Space (padding) | 3 |
| 60-69 | 0-9 | 10 |
| 70 | `-` | 1 |
| 71 | `.` | 1 |
| 72 | `:` | 1 |
| 73 | `/` | 1 |
| 74 | `?` | 1 |
| 75 | `!` | 1 |
| 76 | `&` | 1 |
| 77 | `@` | 1 |
| 78 | `(` | 1 |
| 79 | `)` | 1 |

**Total: 80 entries** (62 unique characters + 8 space-padding entries)

The credit strings in the file are stored as raw ASCII, but the rendering code uses this table to map internal font glyph indices to the ASCII character being displayed. The credits use a separate font area (likely in `COMM.IMG`'s right-half or UI region) rather than the main 12x12 dialogue font.

## BSS Region (0x304C - 0x18FFF)

90,036 bytes (87.9 KB) of zero-filled space. At runtime (RAM `0x80029000`+), this stores:
- Animation state variables (scroll position, fade alpha, timing counters)
- Display list buffers for GPU rendering
- Current page/scroll index tracking
- Frame counter for timing-based transitions

The LUI reference analysis shows 18 references to `0x80030000` (deep BSS), suggesting significant runtime buffer usage.

## Module Comparison

| Property | SDIC | SMITH | YGUILD | YSHOP | YPROP | YSEG | **YEND** |
|----------|------|-------|--------|-------|-------|------|----------|
| File size | 102,400 | 102,400 | 102,400 | 102,400 | 102,400 | 102,400 | **102,400** |
| Load address | 0x80026000 | 0x80028000 | 0x80026000 | 0x80026000 | 0x80026000 | 0x80026000 | **0x80026000** |
| Code size | ~17 KB | 25.2 KB | 14.3 KB | 11.6 KB | 14.7 KB | 4.8 KB | **5.6 KB** |
| Functions | ~75 | 108 | 78 | ~62 | ~62 | 27 | **~34** |
| Text strings | 555 | 628 | 363 | 0 | 0 | 0 | **155** |
| Text encoding | Game custom | Game custom | Game custom | -- | -- | -- | **ASCII (custom LUT)** |
| Data tables | Text ptrs | Item data + ptrs | Reward + 3 ptr tables | Tile IDs + panels | Tile IDs + panels + stat config | Tile IDs + panels + render | **Dispatch + jump + struct table** |
| BSS size | ~50 KB | 22 KB | ~64 KB | 88 KB | 85 KB | 95 KB | **88 KB** |
| Ext calls | Mixed | 491 ptrs | Moderate | 56 | 76 | 40 | **26 unique (106 total JAL)** |

### Load Address Group

All six `0x80026000` overlays:

| Module | Purpose | Text | Code Size |
|--------|---------|------|-----------|
| **SDIC.BIN** | System Dialogue Controller | 555 strings (game encoding) | ~17 KB |
| **YGUILD.BIN** | Hunter's Guild quest system | 363 strings (game encoding) | 14.3 KB |
| **YPROP.BIN** | Character status screen | 0 | 14.7 KB |
| **YSHOP.BIN** | Shop buy/sell interface | 0 | 11.6 KB |
| **YEND.BIN** | Ending credits | 155 strings (ASCII) | 5.6 KB |
| **YSEG.BIN** | Character segment/formation | 0 | 4.8 KB |

## Relevance to Korean Translation

### Text that needs translation

YEND.BIN contains **155 ASCII credit strings** totaling ~2,852 raw bytes. These consist of:

1. **18 section headers**: Role labels like "Producer:", "Director:", "Graphic:"
2. **124 staff names**: Romanized Japanese names (no translation needed for names)
3. **12 character names**: Voice cast character names like "ELC", "LIEZA", "SHU"
4. **1 song title + credit**: "Song Title: Musicman", " by Cara Jones(SHANTE)"

### Translation considerations

1. **Section headers only**: Only the 18 section headers (e.g., "Producer:" → "프로듀서:") would need Korean translation. Staff names are in romaji and should remain as-is.

2. **ASCII encoding**: Unlike other game files that use the custom game text encoding, YEND.BIN uses plain ASCII through an 80-byte lookup table. To display Korean in the credits, the lookup table at `0x2FFC` would need to be expanded or replaced, and the credit rendering code would need modification to use the game's main font (which would contain Korean glyphs after COMM.IMG modification).

3. **Character name labels**: The voice cast section pairs character names (e.g., "ELC", "LIEZA") with voice actor names. The character names could optionally be translated to Korean (e.g., "엘크", "리자") but this requires switching from the ASCII encoding system to the game's main text encoding, which would mean modifying the rendering code.

4. **Struct table pointers**: The 214-entry struct table at `0x22A0` uses absolute RAM pointers to reference strings. If strings are moved or resized, all pointers must be updated: `new_ptr = 0x80026000 + new_file_offset`.

### Modification approach

**Minimal approach** (header translation only):
1. Replace the 18 section header strings with Korean equivalents
2. Since Korean text requires the game's custom encoding (not ASCII), modify the rendering code at `0x0C48` to use `render_string()` from SCPS_100.26 (`0x800C3254`) instead of the custom ASCII renderer
3. Update string pointers in the struct table
4. Update the character encoding lookup table or bypass it entirely

**No-change approach**:
- The credits are in English/romaji and are perfectly readable without translation
- This is the lowest-priority file for Korean localization since credits convey factual information (staff names) that doesn't change with language

### Available space

The text region currently uses 2,852 bytes. Korean translations of the 18 section headers would be roughly the same size or smaller (e.g., "프로듀서:" encoded in the game's custom format). The BSS region provides 90 KB of space, though modifying BSS boundaries requires care with runtime variable addresses.

### Dependencies

| File | Role |
|------|------|
| `YEND.BIN` | Credits code + text (this file) |
| `COMM.IMG` | Font texture (character glyphs for both ASCII credit font and main game font) |
| `SCPS_100.26` | Main executable: rendering functions, GPU primitives, timing |
