# SDIC.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `SDIC.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay + embedded text dictionary |
| Load address | RAM `0x80026000` |
| Active data | 39,824 bytes (38.9 KB, 38.9% of file) |
| Zero padding | 62,576 bytes (61.1 KB, 61.1% of file) |
| Contains text | **Yes** -- 555 translatable text entries |

## Purpose

SDIC.BIN is the **System Dialogue Controller** -- a dynamically-loaded PS1 MIPS overlay that handles all in-game text rendering. It manages dialogue windows, renders character glyphs from the `COMM.IMG` font texture, processes text control codes, and stores an embedded dictionary of system text (character profiles, monster encyclopedia entries, and profile labels).

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0400F` | 16,400 bytes (16.0 KB) | **MIPS Code** | 21 functions, PS1 R3000A machine code |
| `0x04010`-`0x05B4F` | 6,976 bytes (6.8 KB) | **Binary Data** | High-entropy data (7.26 bits/byte), likely dialogue window texture/sprite |
| `0x05B50`-`0x05F4B` | 1,020 bytes | **Pointer Table** | 255 x 4-byte LE pointers (table-relative offsets) |
| `0x05F4C`-`0x0644B` | 1,280 bytes | **Sub-Pointer Tables** | 20 x 16 x 4-byte sub-pointers for character profiles |
| `0x0644C`-`0x09B8F` | 14,148 bytes (13.8 KB) | **Text Data** | 555 null-terminated text strings |
| `0x09B90`-`0x18FFF` | 62,576 bytes (61.1 KB) | **Zero Padding** | Sector-aligned padding to 100 KB |

### Shannon Entropy by Region

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | 3.32 bits/byte | Low overall (dominated by zero padding) |
| MIPS Code | ~6.0 bits/byte | Typical for compiled MIPS code |
| Binary Data | 7.26 bits/byte | Near-maximum; compressed or texture data |
| Text Data | ~5.5 bits/byte | Typical for encoded Japanese game text |

## MIPS Code Region (0x00000 - 0x0400F)

### Function Table

The code region contains 21 functions. Key functions identified by disassembly:

| File Offset | RAM Address | Function | Frame Size | Description |
|-------------|-------------|----------|------------|-------------|
| `0x00004` | `0x80026004` | `init` | 48 | Module initialization, sets up global pointers |
| `0x001A4` | `0x800261A4` | `func_01` | 40 | Internal setup |
| `0x0061C` | `0x8002661C` | `func_02` | 72 | Internal logic |
| `0x008F0` | `0x800268F0` | `func_03` | 32 | Internal logic |
| `0x009D8` | `0x800269D8` | `func_04` | 64 | Internal logic |
| `0x00E00` | `0x80026E00` | `func_05` | 168 | Complex function (large frame) |
| `0x012D0` | `0x800272D0` | `func_06` | 24 | Small utility |
| `0x01438` | `0x80027438` | `dialogue_mgr` | 88 | Dialogue window lifecycle management |
| `0x016D4` | `0x800276D4` | `func_08` | 40 | Internal logic |
| `0x018A8` | `0x800278A8` | `func_09` | 32 | Internal logic |
| `0x01988` | `0x80027988` | `func_10` | 24 | Small utility |
| `0x01A60` | `0x80027A60` | `func_11` | 72 | Internal logic |
| `0x01E90` | `0x80027E90` | **`render_char`** | 64 | Renders a single character glyph |
| `0x02078` | `0x80028078` | **`render_string`** | 104 | Iterates text bytes, dispatches rendering |
| `0x026D0` | `0x800286D0` | `func_14` | 112 | Complex rendering helper |
| `0x03608` | `0x80029608` | `func_15` | 144 | Largest function; likely window draw/layout |
| `0x03B18` | `0x80029B18` | **`lookup_text`** | 32 | Resolves entry ID to text pointer |
| `0x03C18` | `0x80029C18` | **`render_dict_entry`** | 88 | Renders a dictionary text entry by ID |
| `0x03D88` | `0x80029D88` | `func_18` | 40 | Internal logic |
| `0x03F24` | `0x80029F24` | `func_19` | 32 | Internal logic |
| `0x03F98` | `0x80029F98` | `func_20` | 32 | Internal logic |

### Key Function Details

#### `render_char` (0x01E90 / 0x80027E90)

Renders a single 12x12 character glyph from the COMM.IMG font texture. Called with parameters:

```
render_char(y, x, width=12, height=12, charID, color)
```

The charID-to-texture-coordinate conversion uses division by 84 (= 21 columns x 4 bitplanes):

```
adjusted = charID - 1
row      = adjusted / 84
col_rem  = adjusted % 84
col      = col_rem / 4
bitplane = col_rem % 4
u        = col * 12      (texture X coordinate)
v        = row * 12      (texture Y coordinate)
```

The CLUT is selected based on the bitplane value to isolate the correct character layer from the 4bpp data.

#### `render_string` (0x02078 / 0x80028078)

Main text rendering loop. Reads bytes from a text buffer and dispatches:
- Single-byte characters (0x01-0xEE): direct charID, calls `render_char`
- Two-byte characters (0xF0-0xF5 + XX): extended charID, calls `render_char`
- Control codes (0xFF + sub + param1 + param2): dispatched to control handlers in the main executable
- Choice prefix (0xEF): marks a selectable option
- Null (0x00): string terminator

#### `lookup_text` (0x03B18 / 0x80029B18)

Resolves a text entry ID to a memory pointer. Two paths:

**Entries 1-20 (character profiles):** Computes a pointer into a character data structure array at RAM `0x800BD424`. Each structure is 260 bytes; the text pointer is at offset +220 (`0xDC`). This path calls through the main executable (`0x800D8B78`) which manages character state.

**Entries >= 21 (dictionary):** Calls a function at `0x8015D470` in the main executable, which uses the pointer table at `0x8002BB50` to locate text data within SDIC.BIN.

#### `render_dict_entry` (0x03C18 / 0x80029C18)

Renders a complete dictionary text entry at a given screen position. Contains the core pointer resolution logic:

```c
// s1 = 0x8002BB50 (pointer table base = file offset 0x5B50)
// For entries 1-20: two-level lookup
//   ptr = table[entry_id - 1]         // sub-table offset
//   text_addr = table_base + ptr      // sub-table address
//   sub_ptr = sub_table[sub_index]    // text offset
//   final_addr = table_base + sub_ptr // text address
//
// For entries >= 21: single-level lookup
//   ptr = table[entry_id - 1]         // text offset
//   text_addr = table_base + ptr      // text address
```

After resolving the text address, it loops through characters calling a decoder function (`0x8015126C`) and `render_char` (`0x80027E90`). Line wrapping occurs after 11 characters or at punctuation marks `、` (0xE4) and `。` (0xEC), with a vertical advance of 13 pixels per line.

## Binary Data Region (0x04010 - 0x05B4F)

| Property | Value |
|----------|-------|
| Size | 6,976 bytes |
| Shannon entropy | 7.26 bits/byte |
| Null bytes | 46 (0.7%) |
| Unique byte values | 255 of 256 |

This region has near-maximum entropy and very few null bytes, suggesting it contains either compressed data or tightly-packed pixel/sprite data. Given SDIC.BIN's role as the dialogue controller, this is most likely a **dialogue window border/frame texture** or **UI sprite sheet** used to render the text box background and decorations.

The data is not a standard PS1 TIM image (no TIM header `0x10000000`). It may be a raw 4bpp or 8bpp texture loaded directly to VRAM by the initialization code.

## Pointer Table Structure (0x05B50)

The pointer table is at file offset `0x5B50` (RAM `0x8002BB50`). All pointer values are **offsets relative to the table base address**, not absolute addresses.

### Layout

```
Table Base (0x5B50)
  ├── Entries 0-19:   20 x 4-byte pointers → sub-pointer tables
  ├── Entries 20-254: 235 x 4-byte pointers → text data (direct)
  │
Sub-Tables (0x5F4C)
  ├── Sub-table 0:    16 x 4-byte pointers → text data (entry 0 sub-entries)
  ├── Sub-table 1:    16 x 4-byte pointers → text data (entry 1 sub-entries)
  ├── ...
  └── Sub-table 19:   16 x 4-byte pointers → text data (entry 19 sub-entries)
  │
Text Data (0x644C)
  ├── Character profile descriptions
  ├── Profile page labels ("アークプロフィール01" etc.)
  ├── Monster encyclopedia entries
  └── Profile placeholder strings
```

### Pointer Resolution

To resolve a text pointer from the table:

```
file_offset = 0x5B50 + pointer_value
```

For entries 0-19 (two-level):

```
sub_table_file_offset = 0x5B50 + table[entry_id]
text_file_offset      = 0x5B50 + sub_table[sub_index]
```

### First 20 Entries: Fixed-Size Sub-Tables

Entries 0-19 each point to a 64-byte sub-pointer table containing 16 x 4-byte pointers. These sub-tables are evenly spaced at `0x40` (64 byte) intervals starting from pointer offset `0x3FC`.

| Entry | Pointer | Sub-Table File Offset | Character |
|-------|---------|----------------------|-----------|
| 0 | `0x003FC` | `0x05F4C` | アーク (Arc) |
| 1 | `0x0043C` | `0x05F8C` | ポコ (Poco) |
| 2 | `0x0047C` | `0x05FCC` | トッシュ (Tosh) |
| 3 | `0x004BC` | `0x0600C` | イーガ (Iga) |
| 4 | `0x004FC` | `0x0604C` | ゴーゲン (Gogen) |
| 5 | `0x0053C` | `0x0608C` | エルク (Elk) |
| 6 | `0x0057C` | `0x060CC` | リーザ (Lieza) |
| 7 | `0x005BC` | `0x0610C` | シャンテ (Shante) |
| 8 | `0x005FC` | `0x0614C` | シュウ (Shu) |
| 9 | `0x0063C` | `0x0618C` | ヂークベック (Diekbeck) |
| 10 | `0x0067C` | `0x061CC` | サニア (Sania) |
| 11 | `0x006BC` | `0x0620C` | グルガ (Gruga) |
| 12 | `0x006FC` | `0x0624C` | ケラック (Kelack) |
| 13 | `0x0073C` | `0x0628C` | モフリー (Mofree) |
| 14 | `0x0077C` | `0x062CC` | ヘモジー (Hemoji) |
| 15 | `0x007BC` | `0x0630C` | フウジン (Fujin) |
| 16 | `0x007FC` | `0x0634C` | ライジン (Raijin) |
| 17 | `0x0083C` | `0x0638C` | オドン (Odon) |
| 18 | `0x0087C` | `0x063CC` | ククル (Kukuru) |
| 19 | `0x008BC` | `0x0640C` | ちょこ (Choko) |

Each sub-table contains 16 entries:
- Sub-entry 0: Character description text
- Sub-entries 1-15: Profile page labels (e.g., "アークプロフィール01" through "プロフィール15")

## Text Data Content

### Summary

| Category | Entry Range | Count | Description |
|----------|-------------|-------|-------------|
| Character profiles | 0-19 (sub-tables) | 320 | 20 characters x 16 sub-entries (description + 15 profile labels) |
| Extra profile labels | 20-23 | 4 | "プロフィール021" through "プロフィール024" |
| Monster encyclopedia | 24-225 | 202 | Monster/creature descriptions narrated by ちょこ (Choko) |
| Profile placeholders | 226-254 | 29 | Repeated "プロフィール" strings |
| **Total** | | **555** | |

### Character Profile Descriptions (Entries 0-19, Sub-entry 0)

Each character has a personality description written from the perspective of a young narrator. Examples:

| Entry | Character | Description (decoded) |
|-------|-----------|----------------------|
| 0 | アーク | Description of Arc's personality |
| 5 | エルク | 士のお躍代。... (Elk's description) |
| 9 | ヂークベック | 紛なカッコのロボットさん。... (Diekbeck's robot description) |
| 11 | グルガ | いつもハダカでカゼひかないのかな？ (Always naked, doesn't he catch a cold?) |

### Monster Encyclopedia (Entries 24-225)

202 monster description entries, narrated from the first-person perspective of ちょこ (Choko), a party member. These describe monster appearances, behaviors, attack patterns, and weaknesses. Examples:

| Entry | Content |
|-------|---------|
| 24 | Description of a fire monster |
| 41 | Description of a zombie creature |
| 47 | "ねぇねぇ、モンスターが妨編を償えるとき..." (Hey, when monsters learn skills...) |
| 65 | Description of a black dragon-like monster |
| 131 | "こんなに巨いモンスターがいるなんてびっくり！" (I can't believe there are monsters this big!) |
| 218 | "スライムがね、スライムがね、かみつくの！" (The slime, the slime bites!) |

### Profile Labels (Entries 1-15 within each sub-table, and entries 20-254)

Short label strings used by the profile viewer UI:
- "アークプロフィール01" through "アークプロフィール15" (for each character)
- "プロフィール021" through "プロフィール024" (generic)
- "プロフィール" x 29 (placeholder strings for unused profile slots)

## Text Encoding

Text strings in SDIC.BIN use the same encoding as all other game files (see `TEXT_ENCODING.md`):

| Byte Range | Encoding | CharID Range |
|------------|----------|--------------|
| `0x00` | Null terminator | -- |
| `0x01`-`0xEE` | Single byte | 1-238 |
| `0xEF` | Choice option prefix | -- |
| `0xF0 XX`-`0xF5 XX` | Two bytes | 239-1768 |
| `0xFF sub p1 p2` | Control code | -- |

## Rendering Pipeline

The text rendering flow in SDIC.BIN:

```
1. Game calls render_dict_entry(entry_id, x, y)
2. render_dict_entry resolves entry_id to a text pointer:
   - Entries 1-20: two-level lookup via sub-pointer tables
   - Entries 21+: single-level lookup from pointer table
3. Text pointer → byte stream loop:
   a. Read next byte(s) from text buffer
   b. Decode charID (single-byte or two-byte encoding)
   c. Call render_char(y, x, 12, 12, charID, color)
   d. Advance x by 12 pixels
   e. If character count reaches 11 or punctuation hit:
      - Reset x to left margin
      - Advance y by 13 pixels
   f. Repeat until null terminator
```

### Line Wrapping Constants

| Constant | Value | Usage |
|----------|-------|-------|
| Characters per line | 11 | Maximum before auto-wrap |
| Horizontal advance | 12 pixels | Per character (11px glyph + 1px margin) |
| Vertical advance | 13 pixels | Per line (12px cell + 1px gap) |
| Line-break triggers | `、` (0xE4), `。` (0xEC) | Japanese punctuation forces newline |

## Relevance to Korean Translation

### Text that needs translation

SDIC.BIN contains **555 translatable text entries** totaling ~17,827 raw bytes:

1. **20 character descriptions** (sub-entry 0 of entries 0-19): Personality/lore descriptions of each playable character
2. **202 monster encyclopedia entries** (entries 24-225): In-game bestiary descriptions
3. **333 profile/label strings** (sub-entries 1-15, entries 20-23, 226-254): UI labels like "プロフィール01"

### Code modifications required

For a font-swap-only approach (replacing Japanese glyphs with Korean in COMM.IMG), the text data in SDIC.BIN can be modified in-place. The pointer table structure must be updated if string lengths change.

If implementing **jamo composition** (assembling Hangul from component parts), the `render_char` function at `0x01E90` would need to be patched to compose 2-3 jamo glyphs into a single character cell. This function is the single point where charID-to-texture mapping occurs.

### Pointer table modification

When translating text strings, their lengths will change. The pointer table values must be recalculated:

```
new_pointer = old_table_base_offset + new_text_offset_from_table_base
```

Since all pointers are relative to the table base (`0x5B50`), the approach is:
1. Keep the pointer table at `0x5B50`
2. Rewrite all text data after the sub-pointer tables
3. Update all pointer values in the main table and sub-tables
4. Ensure the total data (table + sub-tables + text) fits within the available space before zero padding (currently ends at `0x09B90`, with 62 KB of unused space extending to `0x19000`)

The 62 KB of zero padding provides substantial room for text expansion. Korean text is typically comparable in byte-length to Japanese for this encoding, so space should not be an issue.

### Files in the rendering pipeline

| File | Role in text rendering |
|------|----------------------|
| `SDIC.BIN` | Code + dictionary text (this file) |
| `COMM.IMG` | Font texture (character glyphs) |
| `SCPS_100.26` | Main executable: control code dispatcher, SJIS mapping tables |
| `S*.STG` | Stage dialogue (uses SDIC.BIN's render functions at runtime) |
