# SCPS_100.26 Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `SCPS_100.26` |
| Size | 909,312 bytes (888 KB, 0xDE000) |
| Sectors | 444 CD-ROM sectors (2,048 bytes each) |
| Type | PS1 main executable (PSX-EXE format) |
| Region | Japan (NTSC-J) -- "Sony Computer Entertainment Inc. for Japan area" |
| Load address | RAM `0x800C1400` |
| Entry point | RAM `0x80167E1C` (file offset `0x0A6A1C`) |
| RAM range | `0x800C1400` -- `0x8019EC00` (907,264 bytes) |
| BSS range | `0x8019E850` -- `0x801FC834` (cleared by entry point) |
| Stack pointer | `0x801FFFF0` (top of 2 MB PS1 RAM) |
| Contains text | **Yes** -- ~84 extractable strings (system menus, error messages, descriptions) |

### Address Conversion

```
file_offset = RAM_address - 0x800C1400 + 0x800
RAM_address = file_offset - 0x800 + 0x800C1400
```

## PSX-EXE Header (0x000 - 0x7FF)

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x000 | 8 | Magic | `PS-X EXE` |
| 0x010 | 4 | Entry point (PC) | `0x80167E1C` |
| 0x014 | 4 | GP register | `0x00000000` (unused) |
| 0x018 | 4 | Load address (t_addr) | `0x800C1400` |
| 0x01C | 4 | Text size (t_size) | `0x000DD800` (907,264 bytes) |
| 0x020 | 4 | Data section address | `0x00000000` (unused) |
| 0x024 | 4 | Data section size | `0x00000000` (unused) |
| 0x028 | 4 | BSS start | `0x00000000` (unused) |
| 0x02C | 4 | BSS size | `0x00000000` (unused) |
| 0x030 | 4 | SP base | `0x801FFFF0` |
| 0x034 | 4 | SP offset | `0x00000000` |
| 0x04C | 47 | Region string | `Sony Computer Entertainment Inc. for Japan area` |
| 0x080-0x7FF | 1,920 | Padding | All zeros |

The body (file offset 0x800 onward, 907,264 bytes) exactly matches the declared t_size. GP, BSS, and data section fields are unused -- the game manages its own BSS initialization via the entry point code.

## PS1 Memory Map

```
0x80000000  +--------------------------+  PS1 RAM start (2 MB)
            |  Kernel / BIOS scratch   |
0x80010000  +--------------------------+  COMM.DAT battle module (66 KB)
0x80026000  +--------------------------+  UI overlays (mutually exclusive, 100 KB)
0x80028000  |  SMITH.BIN (coexists)    |
            |                          |
0x800C1400  +==========================+  <-- SCPS_100.26 load address
            |                          |
            |  Main executable code    |  (747 KB code body)
            |                          |
0x8017F134  |  SJIS mapping tables     |
            |  Encoding support data   |
0x80181D00  |  Name/item tables        |
            |  Pointer tables, config  |
0x80193200  |  Game text strings       |  (~21 KB, 960 strings)
            |  Stat glyph table        |
            |  Dense kanji text        |
0x80198600  |  Late code + data        |
            |                          |
0x8019EC00  +==========================+  <-- End of loaded region
0x8019E850  |  BSS (cleared at boot)   |  ~24 KB
0x801FC834  +--------------------------+  End of BSS
            |  Free (stack space)      |
0x801FFFF0  +--------------------------+  <-- SP (stack, grows down)
0x80200000  +--------------------------+  PS1 2 MB RAM end
```

## File Layout

| File Offset | RAM Address | Size | Description |
|-------------|-------------|------|-------------|
| `0x000000` | -- | 2,048 | PSX-EXE header |
| `0x000800` | `0x800C1400` | 3,968 | Jump/dispatch tables, debug strings |
| `0x001780` | `0x800C2380` | 747,648 | **Main MIPS code body** |
| `0x0B8000` | `0x80178C00` | 16,384 | Mixed code/data (GPU/SPU) |
| `0x0BC000` | `0x8017CC00` | 7,424 | Late utility functions |
| `0x0BDD00` | `0x8017E900` | 2,100 | Data/pointer tables |
| `0x0BE534` | `0x8017F134` | 980 | **SJIS character mapping tables** |
| `0x0BE908` | `0x8017F508` | 1,528 | Encoding support tables |
| `0x0BEF00` | `0x8017FB00` | 8,704 | Name/item string tables (secondary text) |
| `0x0C1100` | `0x80181D00` | 70,912 | Mixed structures, code, pointer tables, config |
| `0x0D2600` | `0x80193200` | 10,560 | **Game text** (items, skills, UI labels) |
| `0x0D4F40` | `0x80195B40` | 60 | Stat glyph table (10 entries) |
| `0x0D4F7C` | `0x80195B7C` | 10,884 | **Game text** (descriptions, locations, movies) |
| `0x0D7A00` | `0x80198600` | 25,344 | Late code, data, math/trig tables, padding |

### Entropy Profile

| Region | Entropy | Null % | Classification |
|--------|---------|--------|----------------|
| Header (0x000000) | 3.6 | 54% | Sparse header |
| Code body (0x000800-0x0B8000) | 5.0-5.7 | 22-33% | MIPS R3000A code |
| SJIS tables (0x0BE534) | 5.0-5.2 | 30-40% | Structured lookup data |
| Text region (0x0D2600-0x0D7A00) | 6.0-6.7 | 11-17% | Dense game text (F0-F5 kanji heavy) |
| Math tables (0x0DA800-0x0DC000) | 6.8-6.9 | 1.6% | Numeric data (trig/lookup) |

The text region has notably higher entropy than code due to dense two-byte kanji encoding (F0-F5 prefix sequences).

## Entry Point

The entry point at `0x80167E1C` (file `0x0A6A1C`) is **not** at the start of the loaded region. There is ~682 KB of code/data before it. The entry point begins with a BSS-clearing loop:

```mips
0x80167E1C: lui   $2, 0x801A       ; $2 = 0x8019E850 (BSS start)
0x80167E20: addiu $2, $2, -0x17B0
0x80167E24: lui   $3, 0x8020       ; $3 = 0x801FC834 (BSS end)
0x80167E28: addiu $3, $3, -0x37CC
0x80167E2C: sw    $0, 0($2)        ; clear word
0x80167E30: addiu $2, $2, 4        ; advance pointer
0x80167E34: sltu  $1, $2, $3       ; loop until $2 >= $3
0x80167E38: bne   $1, $0, -0x10
```

This clears ~24 KB of BSS (0x8019E850 to 0x801FC834) before proceeding to game initialization.

## Text Data

### Overview

| Property | Value |
|----------|-------|
| Main text region | File `0x0D2600` -- `0x0D7A00` (21,504 bytes) |
| Secondary text region | File `0x0BEF00` -- `0x0C1100` (8,704 bytes) |
| Extractable strings | **84** (after strict filtering) |
| Raw scan candidates | 21,090 (mostly MIPS code false positives) |
| Encoding | Game custom (same as STG/BIN files, see `TEXT_ENCODING.md`) |

### Decoding Challenges

SCPS_100.26 is a PS1 executable containing ~888 KB of MIPS R3000A machine code. Unlike dialogue-focused files (STG, SDIC.BIN), most of the file is compiled code rather than text data. This creates significant challenges for text extraction:

**The problem**: MIPS instruction bytes frequently map to valid game character IDs, producing long runs of nonsensical kana/kanji that appear to be text but are actually machine code. For example, the byte sequence `0x28 0x01` (a common MIPS instruction pattern) decodes to "りあ" in the game's encoding.

**Solution**: The decoder uses a **strict filter** for executable files that requires:
1. Proper Japanese sentence endings (ます、です、ません、か、etc.)
2. Rejection of repetitive patterns (e.g., "ギギギ" from code loops)
3. Rejection of excessive katakana "ギ" (charID 0x07, very common in MIPS code)
4. Rejection of Latin letters mixed randomly with Japanese
5. Balanced hiragana/katakana ratio checks

This reduces 21,090 raw candidates to **84 verified text strings**, concentrated in the `0x0D3xxx` region where actual game text is stored.

### Extracted Text Categories (84 strings)

The strict filter extracts strings that have proper Japanese sentence structure. Most extracted strings are from the `0x0D3xxx`-`0x0D6xxx` range:

| Category | Count | File Offset Range | Description |
|----------|-------|-------------------|-------------|
| System messages | ~15 | 0x0D34FC-0x0D36C8 | 特殊能力はありません, ゲームが終了していません, etc. |
| Error/restriction messages | ~20 | 0x0D3700-0x0D38E0 | Item/equipment restriction warnings |
| Status effect descriptions | ~15 | 0x0D3C64-0x0D3F00 | Buff/debuff/ailment descriptions |
| Shop dialogue | ~10 | 0x0D4000-0x0D4320 | Buy/sell/trade-in prompts with question marks |
| Skill descriptions | ~15 | 0x0D5770-0x0D62E0 | Full-sentence spell/ability descriptions |
| Synthesis messages | ~10 | 0x0D6780-0x0D68E0 | Crafting/fusion prompts |

**Note**: Many game strings (character names, monster names, item names, location names, menu labels) are **not extracted** by the strict filter because they lack sentence endings. These strings exist in the file but require manual extraction or a region-specific scan. The 84 extracted strings represent the subset with clear sentence structure that can be reliably distinguished from MIPS code bytes.

### Strings NOT Extracted (require manual or region-based extraction)

| Category | Estimated Count | File Offset Range | Reason Not Extracted |
|----------|-----------------|-------------------|---------------------|
| Character names | ~20 | 0x0D26B2-0x0D2700 | No sentence endings (single words) |
| Monster names | ~150 | 0x0D2700-0x0D2A90 | No sentence endings |
| Skill/ability names | ~100 | 0x0D2F00-0x0D3260 | No sentence endings |
| Menu/UI labels | ~30 | 0x0D32E0-0x0D33B0 | Short labels without particles |
| Location names | ~200 | 0x0D6900-0x0D7640 | Noun phrases without verb endings |
| FMV labels | 24 | 0x0D7790-0x0D7920 | Short labels (ムービー1~24) |
| Name entry grids | ~35 | 0x0BEF00-0x0C1100 | Character tables, not sentences |

### Example Strings

**Save/load system:**
```
0x0D35D0: メモリーカードが差されていませんが　セーブせずにゲームをしますか？
          (No memory card inserted. Play without saving?)
0x0D3616: メモリーカードが初期化されていませんが初期化しますか？
          (Memory card not formatted. Format?)
0x0D3638: 空きブロックが足りません。セーブせずにゲームをしますか？
          (Not enough free blocks. Play without saving?)
```

**Equipment restrictions:**
```
0x0D376E: 装備できない武器系統です
          (Incompatible weapon type)
0x0D37AE: 反対属性のアイテムを既に装備しています
          (Already equipping opposite-element item)
```

**Skill descriptions:**
```
0x0D5778: 地の底深くから突き出す岩が敵に激突する
          (Rocks thrust up from deep earth striking the enemy)
0x0D627C: 僧侶の得意とする呪文。失った体力を癒す
          (Cleric's specialty spell. Heals lost HP)
```

**Location names:**
```
0x0D6938: エルクのアパート          (Elc's Apartment)
0x0D7182: ロマリア城　謁見の間      (Romalia Castle, Audience Chamber)
0x0D7266: 墜落したロマリア城跡      (Crashed Romalia Castle Ruins)
```

### Stat Glyph Table (File 0x0D4F40)

10 entries of 6 bytes each, embedded within the text region:

```
[FF 0C 01 01 00 00]   →  +1 glyph
[FF 0C 02 01 00 00]   →  +2 glyph
...
[FF 0C 0A 01 00 00]   →  +10 glyph
```

These are self-contained text control sequences (`FF 0C` = insert stat level glyph) used by the battle/level-up system to display stat modifiers. See `TEXT_ENCODING.md` for the charID computation.

## SJIS Character Mapping Tables

### Location

| Property | Value |
|----------|-------|
| File offset | `0x0BE534` |
| RAM address | `0x8017F134` |
| Size | ~980 bytes |
| Purpose | Converts Shift-JIS byte values to internal game charIDs |

### Structure

The table contains **840 mapped entries** organized as multiple sections separated by `00 00` byte pairs:

| Section | Offset | Entries | Content |
|---------|--------|---------|---------|
| 0 | +0x000 | 81 | Hiragana page (charIDs 0x01-0xE3) |
| 2 | +0x068 | 81 | Katakana page (charIDs 0x51-0xE3) |
| 4 | +0x0D0 | 78 | Symbols/extended (charIDs 0xA1-0xEE) |
| 6 | +0x138 | 85 | Alternate kana page (charIDs 0x01-0x55) |
| 8 | +0x1A2 | 130 | Kanji page 1 (charIDs 0x01-0xFD) |

Unmapped entries use the sentinel value `0xEF`. A secondary lookup table at file offset `0x0BE6D4` contains 16-bit (offset, count) pairs indexing into kanji glyph pages (~97 glyphs per SJIS row).

### Dispatch Function (File 0x025484 / RAM 0x800E6084)

A 3-way dispatch function that selects the SJIS decoding mode:

```mips
0x800E6084: addiu $sp, $sp, -24
0x800E6088: lw    $3, 1732($gp)     ; load encoding mode variable
0x800E608C: ori   $2, $0, 0x0001
0x800E6090: beq   $3, $2, +0x44     ; mode 1 → single-byte path
0x800E6098: slti  $2, $3, 2
0x800E609C: beq   $2, $0, +0x14     ; mode 2 → two-byte path
0x800E60A4: beq   $3, $0, +0x20     ; mode 0 → default path
```

### Font Rendering Function (File 0x025800 / RAM 0x800E6400)

Large function with 152-byte stack frame, 9 callee-saved registers. Renders text using the COMM.IMG font with a 14x14 grid layout (17-column variant). References data near the SJIS tables at `0x8017F0xx`, confirming it processes encoded text for display.

## Key Functions

### Exported API (Called by Overlay Modules)

Analysis of all 7 overlay modules (SDIC, SMITH, YGUILD, YSHOP, YPROP, YSEG, YEND) reveals **97 unique SCPS_100.26 functions** called externally. The most heavily used:

| RAM Address | File Offset | Total Calls | Overlays | Function |
|-------------|-------------|-------------|----------|----------|
| `0x800C3254` | `0x01E54` | 66 | 6/7 | **Text rendering / string display** |
| `0x800CF7C8` | `0x0DFC8` | 57 | 5/7 | **Menu/panel draw** |
| `0x800E9BC0` | `0x285C0` | 25 | 3/7 | **Character stat data read** |
| `0x80167D9C` | `0x56F9C` | 25 | 3/7 | **Inventory management** |
| `0x800E8890` | `0x24A90` | 23 | 3/7 | **Item data lookup** |
| `0x8015E910` | `0x54B10` | 22 | 2/7 | **Stat data initialization** |
| `0x800D90E0` | `0x17CE0` | 13 | 1/7 | UI element draw |
| `0x80155C70` | `0x54870` | 13 | 1/7 | Inventory query |
| `0x800F5C30` | `0x34830` | 11 | 1/7 | Sprite/text rendering primitive |
| `0x800EAB18` | `0x29718` | 9 | 1/7 | Price/gold handling |

### Internal Functions

| RAM Address | File Offset | Function |
|-------------|-------------|----------|
| `0x800E6084` | `0x25484` | SJIS-to-charID dispatch (3-way switch) |
| `0x800E6400` | `0x25800` | Font rendering (14x14 grid, 17-column layout) |
| `0x8015178C` | `0x5038C` | Control code dispatcher (FF prefix) |
| `0x800C1C40` | `0x00840` | 16-entry FF control code jump table |
| `0x80167E1C` | `0xA6A1C` | Entry point (BSS clear + init) |

### Control Code Dispatcher

The FF control code handler at `0x8015178C` indexes into a 16-entry jump table at `0x800C1C40` (file `0x00840`). Each entry handles one FF sub-command (FF 01 through FF 10). See `TEXT_ENCODING.md` for the full control code reference.

## Overlay Module Interface

SCPS_100.26 serves as the central hub for all overlay modules. All overlays call functions exclusively within the executable's RAM range (`0x800C1400`-`0x8019EC00`).

### Overlay Call Counts

| Overlay | Load Address | External Targets | Most-Called Function |
|---------|-------------|-----------------|---------------------|
| SDIC.BIN | `0x80026000` | ~20 | Text rendering, dictionary resolution |
| SMITH.BIN | `0x80028000` | ~491* | Item effect handlers (function pointer table) |
| YGUILD.BIN | `0x80026000` | ~51 | Quest state management |
| YSHOP.BIN | `0x80026000` | 56 | `0x800C3254` (29x), `0x800CF7C8` (21x) |
| YPROP.BIN | `0x80026000` | 76 | `0x800E9BC0` (20x), `0x800C3254` (20x) |
| YSEG.BIN | `0x80026000` | 40 | `0x800C3254` (13x), `0x800CF7C8` (11x) |
| YEND.BIN | `0x80026000` | 26 | `0x800F5C30` (11x), `0x8013BEA8` (7x) |

*SMITH.BIN's high count includes function pointers in item effect tables, not all direct JAL calls.

### Shared API Categories

| Category | Key Functions | Description |
|----------|--------------|-------------|
| Text rendering | `0x800C3254`, `0x800C327C` | Display encoded text strings |
| UI layout | `0x800CF7C8`, `0x800D90E0` | Draw menu panels, UI frames |
| Character data | `0x800E9BC0`, `0x8015E910` | Read/initialize character stats |
| Item system | `0x800E8890`, `0x800EA01C`, `0x800EA410` | Item properties, categories, effects |
| Inventory | `0x80167D9C`, `0x80155C70` | Add/remove/query inventory |
| Graphics | `0x800F5C30`, `0x8013BEA8`, `0x800F7330` | GPU primitives, DMA submit, palettes |
| Timing | `0x800C2EB4` | Frame sync / vsync wait |

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **COMM.IMG** | Font texture -- SCPS_100.26 contains the SJIS-to-charID tables and rendering code that reads COMM.IMG glyphs |
| **COMM.DAT** | Battle animation module at `0x80010000` -- called by SCPS_100.26's battle engine |
| **COMM.SND** | Sound bank -- loaded into SPU RAM by SCPS_100.26's sound driver |
| **SDIC.BIN** | System dialogue controller -- loaded by SCPS_100.26 at `0x80026000` |
| **SMITH.BIN** | Item system -- loaded at `0x80028000`, calls SCPS_100.26 for data and SDIC.BIN for text rendering |
| **YGUILD/YSHOP/YPROP/YSEG/YEND.BIN** | UI overlays -- all loaded at `0x80026000`, depend entirely on SCPS_100.26 APIs |
| **S*.STG** | Stage files -- event scripts call SCPS_100.26 functions for dialogue display and game state |
| **BEAM.DAT** | Battle/event text -- referenced by SCPS_100.26's battle subsystem |

## Decoding Tools

### Extraction Command

```bash
python python/decode/decode_all_bin.py
```

This extracts SCPS_100.26 with **strict scan** mode, which filters out MIPS code false positives. Output: `output/decoded/bin/SCPS_100_26.txt`

### Manual Extraction

For strings not captured by the strict filter (names, labels, location names), use the core decoder with region-specific offsets:

```bash
# Scan a specific region for text
python python/decode/decode_text.py SCPS_100.26 --scan

# Decode at a specific offset
python python/decode/decode_text.py SCPS_100.26 0x0D34FC
```

## Relevance to Korean Translation

### What Needs Translation

SCPS_100.26 contains game text strings that require translation. Due to the difficulty of distinguishing text from MIPS code, only **84 strings** are auto-extracted, but the file contains an estimated **~560 total strings** in the text data regions:

| Priority | Content | Translated | Estimated Total |
|----------|---------|------------|-----------------|
| High | System messages, error messages | **45** | ~45 |
| High | Shop dialogue, prompts | **25** | ~25 |
| Medium | Status/skill descriptions | **80** | ~80 |
| Medium | Synthesis messages | **15** | ~15 |
| Low | Character/monster/item names | 0 | ~270 |
| **High** | **Location names** | **68** | ~68 |
| Low | Menu labels, FMV labels | 17 | ~55 |

**Translation Status (2026-02-07)**: 250 strings translated, including all location names (map labels). Location names are found at offsets `0x000D690C`-`0x000D7924` and include city names, building names, and area map labels.

### What Needs Modification

1. **Text data region** (0x0D2600-0x0D7A00): All ~960 strings must be re-encoded with Korean charIDs. The encoding format is identical to STG/BIN files -- same single-byte and two-byte scheme, same FF control codes.

2. **SJIS mapping tables** (0x0BE534): Must be replaced with a Korean-to-charID mapping table. The dispatch function at `0x800E6084` may need modification if the Korean encoding uses a different page structure than SJIS.

3. **Name entry grids** (0x0BEF00-0x0C1100): The hiragana/katakana character selection grids for name input screens must be replaced with a Hangul grid (or romanized input).

### What Does NOT Need Modification

- **Font rendering code**: The render functions (`0x800E6400`, `0x800C3254`) treat characters as opaque charID lookups. They work with any glyphs stored in COMM.IMG.
- **Control code dispatcher**: All FF-prefix control codes are language-agnostic.
- **Overlay module interface**: The 97 API functions are data-driven and do not contain hardcoded text.
- **Boot/init code**: BSS clearing, hardware setup, etc. are language-independent.

### Constraints

- **Fixed region size**: The text data region is ~21 KB. Korean translations must fit within the same space, or adjacent data must be relocated. Korean text is often more compact than Japanese (no hiragana padding), so this is likely achievable.
- **String pointer tables**: Strings are referenced by pointer from code and data tables throughout the executable. Changing string lengths requires updating all pointer references, or using a fixed-size entry format with padding.
- **Shared encoding**: SCPS_100.26's text uses the same encoding as all other game files. The Korean charID mapping must be consistent across the entire game.
