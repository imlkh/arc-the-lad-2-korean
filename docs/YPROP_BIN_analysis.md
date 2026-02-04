# YPROP.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `YPROP.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay -- character status screen controller |
| Load address | RAM `0x80026000` |
| Active data | 15,636 bytes (15.3% of file) |
| BSS region | 86,764 bytes (84.7% of file) |
| Contains text | **No** -- code + UI configuration data only |

## Verdict: No Translatable Text

YPROP.BIN is a **Character Properties/Status Screen Module** -- a dynamically-loaded PS1 MIPS overlay that implements the character status display interface. It contains **0 text strings**. All translatable content (character names, stat labels, equipment names) is rendered by SCPS_100.26 (the main game executable). YPROP.BIN handles only the UI layout: stat panel arrangement, stat bar rendering, tab navigation, and coordinate tables for positioning stat values on screen.

## Purpose

YPROP.BIN implements the **character status/properties screen** where players view character stats (HP, MP, ATK, DEF, etc.), equipped items, abilities, and level progression. It is loaded as a dynamically-swapped overlay at `0x80026000`, the same address used by SDIC.BIN, YGUILD.BIN, and YSHOP.BIN. Only one of these modules can be loaded at a time.

The module's responsibilities include:
- Rendering the character status UI with multiple stat categories
- Drawing stat bars/gauges with threshold-based scaling
- Managing tab navigation between stat pages (base stats, equipment, abilities)
- Positioning stat values, labels, and icons on screen via coordinate tables
- Interfacing with SCPS_100.26 for character data lookup and text rendering

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x03ABF` | 15,040 bytes (14.7 KB) | **MIPS Code** | 60 functions (status screen UI logic) |
| `0x03AC0`-`0x03AC3` | 4 bytes | **Padding** | Post-code alignment zeros |
| `0x03AC4`-`0x03AE7` | 36 bytes | **Tile/Icon ID Table** | 12 x 16-bit VRAM tile indices in 3 groups |
| `0x03AE8`-`0x03BAB` | 196 bytes | **UI Panel Definitions** | 7 x 28-byte panel layout records |
| `0x03BAC`-`0x03BEB` | 64 bytes | **Stat Threshold Tables** | 2 x 8 x 32-bit stat display scaling values |
| `0x03BEC`-`0x03C5B` | 112 bytes | **Category Index Table** | 28 x 32-bit stat category/tab indices |
| `0x03C5C`-`0x03C93` | 56 bytes | **Y-Coordinate Table** | 14 x 32-bit pixel Y-positions for stat rows |
| `0x03C94`-`0x03D13` | 128 bytes | **Render Configuration** | FFFF-delimited blocks with positions, colors, tile coords |
| `0x03D14`-`0x18FFF` | 86,764 bytes (84.7 KB) | **BSS Region** | Runtime variable storage (zero-filled in file) |

## MIPS Code Region (0x00000 - 0x03ABF)

### Entry Point

Unlike other overlay modules, YPROP.BIN has no jump table and no state-reader preamble. It begins directly with a function prologue:

```
0x0000: ADDIU SP, SP, -0x18     ; function prologue
0x0004: SW    RA, 0x10(SP)      ; save return address
0x0008: JAL   0x8015E910        ; call SCPS_100.26 stat data init
...
```

The first function (156 bytes) initializes the status screen by reading character stat data via SCPS_100.26 calls, then computes stat bar display values using the threshold tables.

### Function Summary

| Metric | Value |
|--------|-------|
| Total functions | ~62 (60 with stack frame prologues, 2 leaf functions) |
| Code size | 15,040 bytes (14.7 KB) |
| Internal call targets | 40 unique addresses |
| External call targets | 76 unique addresses (all in SCPS_100.26) |
| Largest function | 1,296 bytes (0x001FFC-0x00250C) |
| Smallest function | 40 bytes (0x001BA8-0x001BD0) |

### Function List

| # | Offset Range | Size | Notes |
|---|-------------|------|-------|
| 0 | `0x000000`-`0x00009B` | 156 B | Stat initialization + bar scaling |
| 1 | `0x00009C`-`0x0000F3` | 88 B | Secondary stat init |
| 2 | `0x0000F4`-`0x000273` | 384 B | Main stat display setup (called 5x) |
| 3 | `0x000274`-`0x0002CB` | 88 B | Stat read helper |
| 4 | `0x0002CC`-`0x000403` | 312 B | Multi-stat compute + display |
| 5 | `0x000404`-`0x00051F` | 284 B | Stat bar renderer (called 2x) |
| 6 | `0x000520`-`0x00094B` | 1,068 B | Full screen renderer (largest early func) |
| 7-12 | `0x00094C`-`0x000DB3` | 1,700 B | Panel draw / category select helpers |
| 13-16 | `0x000DB4`-`0x0013A0` | 1,516 B | Character detail display |
| 17-20 | `0x0013A0`-`0x001550` | 432 B | Tab navigation handlers |
| 21-26 | `0x001550`-`0x001A60` | 1,296 B | Equipment/ability page display |
| 27-35 | `0x001A60`-`0x001D78` | 792 B | Widget helpers (stat labels, icons) |
| 36-44 | `0x001D78`-`0x002584` | 2,060 B | Level-up / stat growth display |
| 40 | `0x001FFC`-`0x00250C` | 1,296 B | Main status loop (largest function) |
| 45-52 | `0x002584`-`0x003058` | 2,772 B | Detailed stat display / comparison |
| 53-59 | `0x003058`-`0x003AC0` | 2,664 B | Scroll/cursor / exit handlers |

### External Dependencies

**Most frequently called SCPS_100.26 functions:**

| Address | Call Count | Likely Purpose |
|---------|-----------|----------------|
| `0x800C3254` | 20x | Text rendering / string display |
| `0x800E9BC0` | 20x | Character stat data read |
| `0x800CF7C8` | 19x | Menu/panel draw utility |
| `0x8015E910` | 17x | Stat data initialization |
| `0x80167D9C` | 8x | Inventory management |
| `0x800E8890` | 6x | Item data lookup |
| `0x800EA410` | 6x | Item category handler |
| `0x800DFCF8` | 6x | UI element positioning |
| `0x800E8C58` | 6x | Equipment stat modifier read |
| `0x8015D470` | 5x | Character ability list |

Notable: `0x800E9BC0` (character stat read) is called 20x -- the most of any external function -- consistent with a module focused on displaying character properties.

### Game State References

| Address | Access | Count | Purpose |
|---------|--------|-------|---------|
| `0x801A9346` | SH (6x) | 6 | Current character selection index |
| `0x8019E3C4` | SW (6x) | 6 | Status screen state / return address |
| `0x801F1CE8` | SW/LW (6x) | 6 | Page transition / confirmation flag |
| `0x800BD3F0` | LW (3x) | 3 | Character party roster pointer |
| `0x801A934A` | LHU (2x) | 2 | Selected tab/page index |
| `0x801A935C` | LW (2x) | 2 | Character data context pointer |

## Data Section (0x03AC0 - 0x03D13)

The data section is 596 bytes containing exclusively UI configuration data -- no text.

### Tile/Icon ID Table (0x3AC4 - 0x3AE7)

Three groups of 16-bit VRAM tile indices for status screen graphical elements. All values exceed the text CharID range (max 440) and are graphic tile references.

| Group | Offset | Values | Count | Description |
|-------|--------|--------|-------|-------------|
| A | `0x3AC4` | 785, 786, 787, 788 | 4 | Stat page tab icons |
| B | `0x3AD0` | 519, 518 | 2 | Navigation arrows (shared with YSHOP) |
| C | `0x3AD8` | 790, 791, 792, 794, 795, 796 | 6 | Stat bar / gauge tiles |

Note: Group B values (519, 518) are identical to YSHOP.BIN's Group B, suggesting shared UI arrow/cursor graphic tiles.

### UI Panel Definitions (0x3AE8 - 0x3BAB)

Seven 28-byte records defining status screen panel positions. Each record has 8 bytes of active data (4 x 16-bit values) followed by 20 bytes of zero padding.

| Panel | Offset | X | Y | Param A | Param B | Likely Function |
|-------|--------|---|---|---------|---------|-----------------|
| 0 | `0x3AE8` | 16 | 20 | 1 | 4 | Stat category tabs (top) |
| 1 | `0x3B04` | 8 | 80 | 1 | 20 | Main stat list area |
| 2 | `0x3B20` | 8 | 18 | 1 | 2 | Character name/class header |
| 3 | `0x3B3C` | 64 | 76 | 1 | 8 | Equipment display panel |
| 4 | `0x3B58` | 192 | 20 | 1 | 2 | Character portrait area (right) |
| 5 | `0x3B74` | 16 | 180 | 1 | 1 | Bottom info bar |
| 6 | `0x3B90` | 16 | 180 | 1 | 1 | Alternate bottom bar |

### Stat Threshold Tables (0x3BAC - 0x3BEB)

Two tables of 8 x 32-bit values used for stat bar display scaling. These control how stat values are mapped to bar/gauge widths on screen.

**Table 1** (0x3BAC) -- Primary stat display thresholds:
```
[400, 110, 120, 130, 140, 160, 180, 200]
```

**Table 2** (0x3BCC) -- Secondary stat display thresholds:
```
[400, 100, 110, 120, 130, 140, 160, 180]
```

Index 0 (400) likely represents HP/MP maximum bar scale. Indices 1-7 (100-200) correspond to individual stat thresholds (ATK, DEF, AGI, etc.) controlling where the bar transitions from one color segment to another.

### Category Index Table (0x3BEC - 0x3C5B)

28 x 32-bit indices controlling stat category assignment for tab pages:

```
[0, 4, 0, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 4, 4, 4, 4, 4, 4, 0]
```

The repeating `1, 2, 3` pattern maps individual stats to their display category:
- **0** = Header/separator
- **1** = Physical stats (HP, ATK, DEF...)
- **2** = Magical stats (MP, M.ATK, M.DEF...)
- **3** = Speed/special stats (AGI, LUK...)
- **4** = Equipment/ability slots

### Y-Coordinate Table (0x3C5C - 0x3C93)

14 x 32-bit pixel Y-positions for stat row placement on screen:

```
[0, 0, 0, 0, 60, 30, 80, 40, 100, 50, 120, 60, 140, 70]
```

The first 4 zeros are placeholder/header entries. The remaining values come in pairs: (60,30), (80,40), (100,50), (120,60), (140,70) -- these position stat labels (column A) and stat values (column B) at regularly spaced Y intervals of 20 pixels per stat row.

### Render Configuration (0x3C94 - 0x3D13)

FFFF-delimited configuration blocks containing sprite page references, stat label tile positions, and color definitions.

**Sprite page blocks** (0x3C94-0x3CAB):
Two blocks defining VRAM texture page coordinates for the status screen background and UI elements. Format: `[flags, x, y, FFFF]`

**Stat label positions** (0x3CAC-0x3CCF):
Tile placement table with (x, y, tileID) triplets for stat labels:

| X | Y | Tile ID | Likely Label |
|---|---|---------|-------------|
| 48 | 16 | 30 | HP label |
| 48 | 24 | 29 | MP label |
| 112 | 16 | 33 | ATK label |
| 112 | 24 | 34 | DEF label |
| 176 | 16 | 39 | AGI label |
| 240 | 16 | 24 | LUK label |

**Color definition** (0x3CD6-0x3CE3):
RGB color values for stat bar rendering:
```
  0x3CD8: RGB(128, 0, 0) = dark red
  0x3CDC: RGB(128, 0, 0) = dark red
  0x3CE0: RGB(128, 128, 128) = gray (background)
```

**Stat value positions** (0x3CE4-0x3D0D):
Coordinate pairs for stat numeric value placement, terminated by `FFFF FFFF FFFF`.

## BSS Region (0x03D14 - 0x18FFF)

The BSS region is 86,764 bytes (84.7 KB), entirely zero-filled in the file.

**Key BSS variables (most referenced):**

| RAM Address | File Offset | Ref Count | Likely Purpose |
|------------|-------------|-----------|----------------|
| `0x8002B37C` | `0x537C` | 21x | Character stat cache / display buffer |
| `0x80029DF8` | `0x3DF8` | 12x | Current page/tab state |
| `0x80029D18` | `0x3D18` | 11x | Selected stat index |
| `0x80029D9C` | `0x3D9C` | 9x | Scroll position |
| `0x80029DF0` | `0x3DF0` | 9x | Animation frame counter |
| `0x80029D16` | `0x3D16` | 8x | Input state |
| `0x8002B350` | `0x5350` | 2x | Stat comparison buffer |
| `0x8002B354` | `0x5354` | 2x | Equipment modifier cache |

The most-referenced BSS address (`0x8002B37C`, 21 accesses) at file offset `0x537C` is deep in the BSS region, suggesting a large structure (likely a character data cache) allocated well past the initial runtime variables.

## Module Comparison

| Property | SDIC.BIN | SMITH.BIN | YGUILD.BIN | YSHOP.BIN | **YPROP.BIN** |
|----------|----------|-----------|------------|-----------|---------------|
| File size | 102,400 | 102,400 | 102,400 | 102,400 | **102,400** |
| Load address | 0x80026000 | 0x80028000 | 0x80026000 | 0x80026000 | **0x80026000** |
| Code size | ~17 KB | 25.2 KB | 14.3 KB | 11.6 KB | **14.7 KB** |
| Functions | ~75 | 108 | 78 | ~62 | **~62** |
| Text strings | 555 | 628 | 363 | 0 | **0** |
| Data section | Text pointers | Item data + ptrs | Reward + 3 ptr tables | Tile IDs + panels | **Tile IDs + panels + stat config** |
| Data size | ~6 KB | ~5.6 KB | ~2.4 KB | 260 B | **596 B** |
| BSS size | ~50 KB | 22 KB | ~64 KB | 88 KB | **85 KB** |
| External calls | Mixed | 491 code ptrs | Moderate | 56 | **76** |

### Load Address Conflicts

YPROP.BIN loads at `0x80026000`, the same address as SDIC.BIN, YGUILD.BIN, and YSHOP.BIN. These four modules are **mutually exclusive**:
- **SDIC.BIN**: General system dialogue (menus, conversations)
- **YGUILD.BIN**: Hunter's Guild quest system
- **YSHOP.BIN**: Shop buy/sell interface
- **YPROP.BIN**: Character status/properties screen

## Relevance to Korean Translation

**YPROP.BIN does not need to be modified for text translation.** It contains no embedded text -- all visible text on the status screen (character names, stat labels, equipment names, ability descriptions) comes from SCPS_100.26 and the stat label tiles embedded in COMM.IMG.

If the Korean font requires different stat label tile indices (because new tiles are added for Korean stat abbreviations), the tile position table at `0x3CAC`-`0x3CCF` would need its tile ID values updated. Similarly, if Korean text spacing differs from Japanese, the coordinate tables at `0x3C5C`-`0x3D0D` may need adjustment to prevent text overlap.
