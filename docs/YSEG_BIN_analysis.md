# YSEG.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `YSEG.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay -- character segment/formation UI |
| Load address | RAM `0x80026000` |
| Active data | 5,100 bytes (5.0% of file) |
| BSS region | 97,300 bytes (95.0% of file) |
| Contains text | **No** -- code + UI configuration data only |

## Verdict: No Translatable Text

YSEG.BIN is the smallest active-data overlay analyzed in this project. It contains **0 text strings** and only 5.0 KB of non-zero data (4.8 KB code + 156 bytes data). The remaining 95% of the file is BSS (runtime variable storage). All translatable content displayed by this module is rendered by SCPS_100.26.

## Purpose

YSEG.BIN implements a **character segment/formation management screen** -- a lightweight overlay for viewing or selecting character deployment segments. Given its small code size (27 functions), 3 UI panels, and references to character stat and inventory functions, this module likely handles a focused sub-screen such as party formation selection or character info display during tactical deployment.

The module is loaded at `0x80026000`, the same address used by SDIC.BIN, YGUILD.BIN, YSHOP.BIN, and YPROP.BIN. Only one of these five overlays can be loaded at a time.

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0134F` | 4,944 bytes (4.8 KB) | **MIPS Code** | 27 functions |
| `0x01350`-`0x0136B` | 28 bytes | **Tile/Icon ID Table** | 8 x 16-bit VRAM tile indices in 3 groups |
| `0x0136C`-`0x013BF` | 84 bytes | **UI Panel Definitions** | 3 x 28-byte panel layout records |
| `0x013C0`-`0x013EB` | 44 bytes | **Render Configuration** | FFFF-delimited coordinate blocks |
| `0x013EC`-`0x18FFF` | 97,300 bytes (95.0 KB) | **BSS Region** | Runtime variable storage (zero-filled in file) |

## MIPS Code Region (0x00000 - 0x0134F)

### Entry Point

YSEG.BIN starts directly with a function prologue -- no jump table or state-reader preamble:

```
0x0000: ADDIU SP, SP, -0x18     ; function prologue
0x0004: SLL   A0, A0, 1         ; parameter shift
0x0008: SW    RA, 0x10(SP)      ; save return address
0x000C: LUI   AT, 0x8002        ; load base for data table
0x0010: ADDIU AT, AT, 0x735E    ; → RAM 0x8002735E (data section)
...
```

The first function (76 bytes) initializes a UI panel by loading tile IDs from the data section and calling SCPS_100.26 rendering functions.

### Function Summary

| Metric | Value |
|--------|-------|
| Total functions | 27 (all with stack frame prologues) |
| Code size | 4,944 bytes (4.8 KB) |
| Internal call targets | 15 unique addresses |
| External call targets | 40 unique addresses (all in SCPS_100.26) |
| Largest function | 840 bytes (0x000388-0x0006D0) |
| Smallest function | 40 bytes (0x000CF0-0x000D18, 0x000DC4-0x000DEC) |

### Function List

| # | Offset Range | Size | Notes |
|---|-------------|------|-------|
| 0 | `0x000000`-`0x00004B` | 76 B | Panel init with tile table |
| 1 | `0x00004C`-`0x0000DB` | 144 B | Multi-panel setup (called 4x) |
| 2 | `0x0000DC`-`0x000123` | 72 B | Cleanup handler |
| 3 | `0x000124`-`0x0001FB` | 216 B | State dispatcher |
| 4 | `0x0001FC`-`0x000237` | 60 B | Screen init |
| 5 | `0x000238`-`0x0002B7` | 128 B | Data loader |
| 6 | `0x0002B8`-`0x000387` | 208 B | Selection handler |
| 7 | `0x000388`-`0x0006CF` | 840 B | Main screen renderer (largest) |
| 8 | `0x0006D0`-`0x0007CF` | 256 B | Character slot display |
| 9 | `0x0007D0`-`0x00093B` | 364 B | Input/cursor handler |
| 10-12 | `0x00093C`-`0x000B07` | 460 B | Selection confirm/cancel |
| 13-20 | `0x000B08`-`0x000DEB` | 740 B | Widget helpers (slot frames, labels) |
| 21 | `0x000DEC`-`0x000F73` | 392 B | Character info renderer (called 3x) |
| 22 | `0x000F74`-`0x00112B` | 440 B | Detail panel draw (called 3x) |
| 23-25 | `0x00112C`-`0x001313` | 488 B | Stat display / comparison |
| 26 | `0x001314`-`0x00134F` | 60 B | Exit/return handler (called 2x) |

### External Dependencies

**Most frequently called SCPS_100.26 functions:**

| Address | Call Count | Likely Purpose |
|---------|-----------|----------------|
| `0x800C3254` | 13x | Text rendering / string display |
| `0x800CF7C8` | 11x | Menu/panel draw utility |
| `0x800E9BC0` | 5x | Character stat data read |
| `0x80167D9C` | 4x | Inventory management |
| `0x800E8C58` | 4x | Equipment stat modifier read |
| `0x800E8890` | 3x | Item data lookup |
| `0x800D8964` | 3x | UI utility function |
| `0x8015E280` | 3x | Character list initialization |

The module calls `0x800C3254` (text rendering) 13 times and `0x800CF7C8` (panel draw) 11 times -- these are the two most common external calls, consistent with a display-focused module.

### Game State References

| Address | Access | Count | Purpose |
|---------|--------|-------|---------|
| `0x801A935C` | LW (2x) | 2 | Character data context pointer |
| `0x801A934C` | LHU (1x) | 1 | Selected character index |
| `0x801F1CE8` | SW (1x) | 1 | Screen transition flag |
| `0x801F1CEC` | SW (1x) | 1 | Return destination |
| `0x801F1B2C` | ADDIU (1x) | 1 | External data structure pointer |

The minimal game state interaction (only 6 references to 5 addresses) confirms this is a focused display-only screen with limited state modification.

## Data Section (0x01350 - 0x013EB)

The data section is only 156 bytes -- the smallest of all analyzed overlays.

### Tile/Icon ID Table (0x1350 - 0x136B)

Three groups of 16-bit VRAM tile indices for UI graphical elements:

| Group | Offset | Values | Count | Description |
|-------|--------|--------|-------|-------------|
| A | `0x1350` | 798, 799 | 2 | Screen-specific border tiles |
| B | `0x1358` | 519, 518 | 2 | Navigation arrows (shared with YSHOP/YPROP) |
| C | `0x1360` | 800, 801, 802, 803 | 4 | Character slot / segment tiles |

Note: Group B values (519, 518) are identical across YSHOP.BIN, YPROP.BIN, and YSEG.BIN -- a shared set of navigation arrow tiles.

### UI Panel Definitions (0x136C - 0x13BF)

Three 28-byte records defining screen panel positions:

| Panel | Offset | X | Y | Param A | Param B | Likely Function |
|-------|--------|---|---|---------|---------|-----------------|
| 0 | `0x136C` | 16 | 20 | 1 | 2 | Character list / segment selector (top) |
| 1 | `0x1388` | 16 | 180 | 1 | 1 | Bottom info/confirm bar |
| 2 | `0x13A4` | 214 | 136 | 1 | 2 | Detail popup (bottom-right) |

Panel 2's position (214, 136) places it in the lower-right corner of the screen -- likely an info popup showing stats or details for the selected character slot.

### Render Configuration (0x13C0 - 0x13EB)

Two FFFF-delimited blocks of coordinate data for UI element rendering:

**Block 1** (0x13C0-0x13CD):
```
48, 0, 28, 0, 40, 24, FFFF
```
Mixed 32-bit (48, 28) and 16-bit (40, 24) values defining a coordinate region, followed by FFFF terminator.

**Block 2** (0x13D4-0x13EB):
```
48, 0, 28, 48, 8, 41, 0, 40, 24, FFFF, FFFF, FFFF
```
Position parameters for secondary UI elements, terminated by triple FFFF.

## BSS Region (0x013EC - 0x18FFF)

The BSS region is 97,300 bytes (95.0 KB) -- the largest proportion of BSS to active data of any analyzed overlay (95% BSS vs 5% code+data).

**Key BSS variables (most referenced):**

| RAM Address | File Offset | Ref Count | Likely Purpose |
|------------|-------------|-----------|----------------|
| `0x80027480` | `0x1480` | 16x | Primary state variable / cursor position |
| `0x80027478` | `0x1478` | 10x | Current selection index |
| `0x80027474` | `0x1474` | 10x | Segment count / list length |
| `0x800273EC` | `0x13EC` | 9x | Screen mode flags (first BSS word) |
| `0x80027484` | `0x1484` | 8x | Selected character data cache |
| `0x80027488` | `0x1488` | 7x | Detail panel data |
| `0x8002747C` | `0x147C` | 7x | Input state |
| `0x800273F0` | `0x13F0` | 5x | Page state |

The first BSS word (`0x800273EC`, 9 refs) serves as the screen's primary mode flag. The most-accessed cluster (`0x80027474`-`0x80027488`, 58 total refs) forms a compact runtime state block of 20 bytes.

## Module Comparison

| Property | SDIC | SMITH | YGUILD | YSHOP | YPROP | **YSEG** |
|----------|------|-------|--------|-------|-------|----------|
| File size | 102,400 | 102,400 | 102,400 | 102,400 | 102,400 | **102,400** |
| Load address | 0x80026000 | 0x80028000 | 0x80026000 | 0x80026000 | 0x80026000 | **0x80026000** |
| Code size | ~17 KB | 25.2 KB | 14.3 KB | 11.6 KB | 14.7 KB | **4.8 KB** |
| Functions | ~75 | 108 | 78 | ~62 | ~62 | **27** |
| Text strings | 555 | 628 | 363 | 0 | 0 | **0** |
| Data size | ~6 KB | ~5.6 KB | ~2.4 KB | 260 B | 596 B | **156 B** |
| BSS size | ~50 KB | 22 KB | ~64 KB | 88 KB | 85 KB | **95 KB** |
| BSS % | 49% | 21% | 63% | 86% | 85% | **95%** |
| Ext calls | Mixed | 491 ptrs | Moderate | 56 | 76 | **40** |

YSEG.BIN is the most compact overlay in the set -- the smallest code, smallest data, fewest functions, and highest BSS-to-active ratio.

### Load Address Group

All five `0x80026000` overlays are now documented:

| Module | Purpose | Text | Code Size |
|--------|---------|------|-----------|
| **SDIC.BIN** | System Dialogue Controller | 555 strings | ~17 KB |
| **YGUILD.BIN** | Hunter's Guild quest system | 363 strings | 14.3 KB |
| **YPROP.BIN** | Character status screen | 0 | 14.7 KB |
| **YSHOP.BIN** | Shop buy/sell interface | 0 | 11.6 KB |
| **YSEG.BIN** | Character segment/formation | 0 | 4.8 KB |

## Relevance to Korean Translation

**YSEG.BIN does not need to be modified for text translation.** It contains no embedded text -- all visible text on this screen is rendered by SCPS_100.26.

If UI layout adjustments are needed for Korean text, only the 3 panel definitions at `0x136C`-`0x13BF` would need modification. Panel 2 (detail popup at x=214, y=136) is the most likely candidate for width adjustment if Korean character info text is longer than the Japanese original.
