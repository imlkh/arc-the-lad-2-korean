# YSHOP.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `YSHOP.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay -- shop UI controller |
| Load address | RAM `0x80026000` |
| Active data | 12,152 bytes (11.9% of file) |
| BSS region | 90,248 bytes (88.1% of file) |
| Contains text | **No** -- purely code + UI configuration data |

## Verdict: No Translatable Text

YSHOP.BIN is a **Shop UI Controller Module** -- a thin overlay that manages the shop buy/sell user interface. It contains **0 text strings**. All translatable content (item names, descriptions, prices) is stored in other modules (primarily SMITH.BIN for item data and SCPS_100.26 for the text rendering system). YSHOP.BIN handles only the UI logic: panel layout, cursor navigation, buy/sell state machines, and inventory interaction.

## Purpose

YSHOP.BIN implements the **in-game shop interface** for buying and selling equipment and items. It is loaded as a dynamically-swapped overlay at `0x80026000`, the same address used by SDIC.BIN (System Dialogue Controller) and YGUILD.BIN (Hunter's Guild). Only one of these modules can be loaded at a time -- the game swaps them in and out as needed.

The module's responsibilities include:
- Rendering shop UI panels (item list, price display, quantity selector)
- Handling user input for browsing, buying, and selling
- Interfacing with SCPS_100.26 for item data lookup and text rendering
- Reading/writing game state (inventory, gold) via shared RAM variables

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0000F` | 16 bytes | **Entry Point** | State reader function (returns shop state from game RAM) |
| `0x00010`-`0x02E73` | 11,876 bytes (11.6 KB) | **MIPS Code** | 59 functions (shop UI logic) |
| `0x02E74`-`0x02EAB` | 56 bytes | **Tile/Icon ID Table** | 22 x 16-bit VRAM tile indices for shop UI elements |
| `0x02EAC`-`0x02F77` | 204 bytes | **UI Panel Definitions** | 8 x 28-byte panel layout records |
| `0x02F78`-`0x18FFF` | 90,248 bytes (88.1 KB) | **BSS Region** | Runtime variable storage (zero-filled in file) |

### Shannon Entropy

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | ~1.1 bits/byte | Very low (88% null bytes from BSS) |
| MIPS Code | ~6.0 bits/byte | Typical for compiled MIPS code |
| Data section | ~3.5 bits/byte | Low -- small tables with many zeros |

## MIPS Code Region (0x00000 - 0x02E73)

### Entry Point (0x0000 - 0x000F)

The file starts with a 4-instruction function (no stack frame prologue) that reads a game state variable and returns it:

```
0x0000: LUI   $v0, 0x801B
0x0004: LW    $v0, -0x6C74($v0)    ; load from 0x801B938C
0x0008: JR    $ra
0x000C: NOP
```

This returns the current shop state/type from the game's global state at `0x801B938C`. Unlike YGUILD.BIN and SMITH.BIN which begin with jump tables, YSHOP.BIN starts directly with executable code.

### Function Summary

| Metric | Value |
|--------|-------|
| Total functions | ~62 (59 with stack frame prologues, 3 leaf functions) |
| Code size | 11,892 bytes (11.6 KB) |
| Internal call targets | 33 unique addresses |
| External call targets | 56 unique addresses (all in SCPS_100.26) |
| Largest function | 808 bytes (0x000938-0x000C60) |
| Smallest function | 32 bytes (0x000044-0x000064) |

### Function List

| # | Offset Range | Size | Notes |
|---|-------------|------|-------|
| 0 | `0x000010`-`0x000043` | 52 B | Initialization wrapper |
| 1 | `0x000044`-`0x000063` | 32 B | Simple wrapper |
| 2 | `0x000064`-`0x00008F` | 44 B | Simple wrapper |
| 3 | `0x000090`-`0x00017B` | 236 B | Shop state dispatcher |
| 4 | `0x00017C`-`0x0001C7` | 76 B | Setup helper |
| 5 | `0x0001C8`-`0x000257` | 144 B | Panel initializer (called 4x internally) |
| 6 | `0x000258`-`0x0002EB` | 148 B | Panel renderer A |
| 7 | `0x0002EC`-`0x0003FB` | 272 B | Panel renderer B (multi-panel) |
| 8 | `0x0003FC`-`0x000443` | 72 B | Cleanup handler |
| 9 | `0x000444`-`0x00057F` | 316 B | Main shop loop handler |
| 10 | `0x000580`-`0x000643` | 196 B | Shop exit/transition |
| 11 | `0x000644`-`0x0008B3` | 624 B | Buy menu handler |
| 12 | `0x0008B4`-`0x000937` | 132 B | Category selector |
| 13 | `0x000938`-`0x000C5F` | 808 B | Item list browser (largest function) |
| 14 | `0x000C60`-`0x000D3F` | 224 B | Price calculator |
| 15 | `0x000D40`-`0x000D7F` | 64 B | Quantity validator |
| 16-17 | `0x000D80`-`0x000E5F` | 224 B | Sell menu helpers |
| 18 | `0x000E60`-`0x00103F` | 480 B | Sell menu handler |
| 19-26 | `0x001040`-`0x001837` | 2,040 B | Inventory display/cursor |
| 27-35 | `0x001838`-`0x001C13` | 988 B | UI widget helpers |
| 36-44 | `0x001C14`-`0x002383` | 1,904 B | Item detail display |
| 45-58 | `0x002384`-`0x002E73` | 2,800 B | Confirmation dialogs / final handlers |

### External Dependencies

YSHOP.BIN makes **zero internal JAL calls to its own code** at the function level -- all function calls are either to other internal functions via local offsets or to SCPS_100.26 (the main game executable). This is characteristic of a pure UI module that delegates all business logic to the main executable.

**Most frequently called SCPS_100.26 functions:**

| Address | Call Count | Likely Purpose |
|---------|-----------|----------------|
| `0x800C3254` | 29x | Text rendering / string display |
| `0x800CF7C8` | 21x | Menu/panel draw utility |
| `0x800E8890` | 14x | Item data lookup |
| `0x80167D9C` | 13x | Inventory management |
| `0x80155C70` | 13x | Inventory query |
| `0x800D90E0` | 13x | UI element draw |
| `0x800EAB18` | 9x | Price/gold handling |
| `0x800E9FE8` | 8x | Equipment stat comparison |
| `0x800EA01C` | 7x | Item property read |
| `0x800EA410` | 6x | Item category handler |

### Game State References

The module reads/writes these global RAM addresses for game state interaction:

| Address | Access | Purpose |
|---------|--------|---------|
| `0x801A934A` | LHU (2x) | Current shop inventory slot |
| `0x801A934C` | LHU (1x) | Selected item index |
| `0x801A935C` | LW (2x) | Shop type/context pointer |
| `0x801A938C` | LW (2x) | Shop state flags |
| `0x801F1CE8` | SW/LW (2x) | Transaction result / confirmation |

## Data Section (0x02E74 - 0x02F77)

The data section is compact (260 bytes) and contains only UI configuration data -- no text.

### Tile/Icon ID Table (0x2E74 - 0x2EAB)

Three groups of 16-bit VRAM tile indices used for shop UI graphical elements (icons, borders, category markers). All values exceed the text CharID range (max 440) and are therefore graphic tile references, not text characters.

| Group | Offset | Values | Count | Description |
|-------|--------|--------|-------|-------------|
| A | `0x2E74` | 724, 725, 727 | 3 | Shop panel border tiles |
| B | `0x2E7C` | 519, 518 | 2 | Category icon tiles |
| C | `0x2E84` | 728-746 (consecutive) | 19 | Item slot / list UI tiles |

Total: 24 tile indices (including null terminators between groups).

### UI Panel Definitions (0x2EAC - 0x2F77)

Eight 28-byte records defining the position and size of shop interface panels. Each record has 8 bytes of active data (4 x 16-bit values) followed by 20 bytes of zero padding. The parameters match PS1 screen coordinates (320x240 resolution).

| Panel | Offset | X | Y | Param A | Param B | Likely Function |
|-------|--------|---|---|---------|---------|-----------------|
| 0 | `0x2EAC` | 16 | 20 | 1 | 3 | Category selector (top-left) |
| 1 | `0x2EC8` | 16 | 74 | 1 | 96 | Main item list (left) |
| 2 | `0x2EE4` | 8 | 18 | 1 | 3 | Alternate category panel |
| 3 | `0x2F00` | 16 | 74 | 1 | 96 | Sell item list (same dims as panel 1) |
| 4 | `0x2F1C` | 16 | 74 | 1 | 2 | Short item list (2 items visible) |
| 5 | `0x2F38` | 16 | 180 | 1 | 1 | Gold/total display (bottom) |
| 6 | `0x2F54` | 60 | 20 | 1 | 1 | Item detail panel (right side) |
| 7 | `0x2F70` | 16 | 180 | 1 | 1 | Confirmation bar (bottom) |

Parameters A and B likely control the number of visible rows/columns or panel height/width in tile units.

## BSS Region (0x02F78 - 0x18FFF)

The BSS region is 90,248 bytes (88.1 KB) -- by far the largest section. It is entirely zero-filled in the file and used for runtime variables when the module is loaded.

**Key BSS variables (most referenced):**

| RAM Address | File Offset | Ref Count | Likely Purpose |
|------------|-------------|-----------|----------------|
| `0x80029014` | `0x3014` | 23x | Current cursor position |
| `0x80029010` | `0x3010` | 17x | Current panel state |
| `0x80029048` | `0x3048` | 14x | Item count / list length |
| `0x80028F8C` | `0x2F8C` | 10x | Active shop mode (buy/sell) |
| `0x800290A0` | `0x30A0` | 7x | Scroll offset |
| `0x80029038` | `0x3038` | 6x | Selected item data cache |
| `0x80029018` | `0x3018` | 5x | Input state |
| `0x8002903C` | `0x303C` | 5x | Price cache |
| `0x8002904C` | `0x304C` | 4x | Transaction quantity |

The large BSS size (88 KB) relative to the code size (12 KB) is notable. Most of this space is likely used for buffering item lists and inventory data loaded from the main executable during shop operation.

## Module Comparison

| Property | SDIC.BIN | SMITH.BIN | YGUILD.BIN | **YSHOP.BIN** |
|----------|----------|-----------|------------|---------------|
| File size | 102,400 | 102,400 | 102,400 | **102,400** |
| Load address | 0x80026000 | 0x80028000 | 0x80026000 | **0x80026000** |
| Code size | ~17 KB | 25.2 KB | 14.3 KB | **11.6 KB** |
| Functions | ~75 | 108 | 78 | **~62** |
| Text strings | 555 | 628 | 363 | **0** |
| Data tables | Text pointer tables | Item data + pointers | Reward + 3 pointer tables | **Tile IDs + UI panels** |
| BSS size | ~50 KB | 22 KB | ~64 KB | **88 KB** |
| External calls | Mixed | 491 code ptrs | Moderate | **56 (SCPS_100.26 only)** |
| Secondary data island | Yes | Yes | Yes | **No** |

YSHOP.BIN is the smallest active-data overlay analyzed so far, with the most code-focused design. It delegates all text rendering and data management to SCPS_100.26.

### Load Address Conflicts

YSHOP.BIN loads at `0x80026000`, the same address as SDIC.BIN and YGUILD.BIN. These three modules are **mutually exclusive** -- only one can be in RAM at a time. The game swaps them depending on context:
- **SDIC.BIN**: General system dialogue (menus, conversations)
- **YGUILD.BIN**: Hunter's Guild quest system
- **YSHOP.BIN**: Shop buy/sell interface

SMITH.BIN loads at a different address (`0x80028000`) and may coexist with any of the `0x80026000` overlays, though the RAM ranges potentially overlap for large BSS regions.

## Relevance to Korean Translation

**YSHOP.BIN does not need to be modified for text translation.** It contains no embedded text -- all visible text in the shop UI (item names, descriptions, prices, button labels) comes from SCPS_100.26 and SMITH.BIN, which contain the actual translatable strings.

If UI layout adjustments are needed to accommodate longer Korean text strings (Korean characters may require different spacing than Japanese), the 8 panel definition records at `0x2EAC`-`0x2F77` could be modified to adjust panel positions and sizes. The 4 parameters per record (X, Y, Param A, Param B) control the on-screen placement of each shop UI element.
