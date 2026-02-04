# SMITH.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `SMITH.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay + embedded item data/text |
| Load address | RAM `0x80028000` |
| Active data | 69,609 bytes (68.0% of file) |
| Zero padding | 32,655 bytes (31.9% of file) |
| Contains text | **Yes** -- 628 translatable description strings |

## Purpose

SMITH.BIN is the **Item/Equipment System Module** -- a dynamically-loaded PS1 MIPS overlay that handles item management, equipment stats, smithing/crafting operations, and item description display. It contains 108 MIPS functions for item logic, extensive data tables mapping items to their properties and effect handlers, and 628 embedded text descriptions covering all weapons, armor, accessories, and consumable items in the game.

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0005F` | 96 bytes | **Jump Table** | 24 function offset entries + 2 `0xFFFFFFFF` sentinels |
| `0x00060`-`0x0006F` | 16 bytes | **Error String + Gap** | "ERR" at `0x68`, padding |
| `0x00070`-`0x00087` | 24 bytes | **Secondary Address Table** | 6 RAM addresses (`0x8002BBxx` range) |
| `0x00088`-`0x062FF` | 25,208 bytes (24.6 KB) | **MIPS Code** | 108 functions, PS1 R3000A machine code |
| `0x06300`-`0x0639F` | 160 bytes | **Item Header Records** | 8 x 20-byte records with item IDs and counters |
| `0x063A0`-`0x063BF` | 32 bytes | **RAM Pointer Table** | 8 x 4-byte RAM addresses to code functions |
| `0x063C0`-`0x0645F` | 160 bytes | **Recipe/Crafting Data** | Item composition byte arrays |
| `0x06460`-`0x06557` | 248 bytes | **Configuration Table** | Smithing/UI parameter blocks |
| `0x06558`-`0x06853` | 764 bytes | **Text Line Pointer Table A** | 191 x 4-byte file offsets (text wrapping positions) |
| `0x06854`-`0x06FFF` | 1,964 bytes | **Code Function Pointer Table** | 491 x 4-byte file offsets to item effect handlers |
| `0x07000`-`0x0728F` | 656 bytes | **Data Offset Table** | 164 x 4-byte file offsets to item data records |
| `0x07290`-`0x0774B` | 1,212 bytes | **Text Line Pointer Table B** | 303 x 4-byte file offsets (description line positions) |
| `0x0774C`-`0x10F31` | 38,886 bytes (38.0 KB) | **Item Description Text** | 628 null-terminated text strings |
| `0x10F32`-`0x164FF` | 21,966 bytes (21.4 KB) | **BSS / Zero Region** | Runtime variable space (all zeros in file) |
| `0x16500`-`0x1663E` | 319 bytes | **Secondary Data Island** | Cross-module RAM pointers + parameter blocks |
| `0x1663F`-`0x18FFF` | 10,689 bytes (10.4 KB) | **Zero Padding** | Alignment to 100 KB |

### Shannon Entropy by Region

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | ~5.01 bits/byte | Moderate (mix of code, text, and zero padding) |
| MIPS Code | ~6.0 bits/byte | Typical for compiled MIPS code |
| Description Text | ~5.5 bits/byte | Typical for encoded Japanese game text |
| Zero regions | 0 bits/byte | Uninitialized padding |

## MIPS Code Region (0x00088 - 0x062FF)

### Overview

The code region is substantially larger than SDIC.BIN's (25,208 bytes vs 16,400 bytes), containing 108 functions handling all item-related game logic. The module manages:
- Item/equipment stat calculations
- Smithing/crafting operations
- Item effect execution (use, equip, unequip)
- Item description text display
- Shop interface logic

### Jump Table (0x0000 - 0x005F)

The file begins with a 26-entry jump table (24 active entries + 2 `0xFFFFFFFF` sentinels) providing entry points for the module's public API:

| Index | RAM Address | File Offset | Notes |
|-------|------------|-------------|-------|
| 0 | `0x80028B24` | `0x0B24` | Primary handler |
| 1-2 | `0x80028B64` | `0x0B64` | Common handler (shared) |
| 3 | `0x80028AA0` | `0x0AA0` | Initialization |
| 4 | `0x80028AC0` | `0x0AC0` | Secondary init |
| 5-22 | `0x80028B64` | `0x0B64` | Common handler (all share same address) |
| 23 | `0x80028B80` | `0x0B80` | Cleanup/shutdown |

Most entries (indices 1-22) share the address `0x80028B64`, indicating a dispatcher function that routes requests internally based on a sub-command parameter.

### Secondary Address Table (0x0070 - 0x0087)

Six RAM addresses pointing to functions within the code region:

| Index | RAM Address | File Offset | Description |
|-------|------------|-------------|-------------|
| 0 | `0x8002BBC0` | `0x03BC0` | Internal handler |
| 1 | `0x8002BBCC` | `0x03BCC` | Internal handler |
| 2 | `0x8002BBD8` | `0x03BD8` | Internal handler |
| 3 | `0x8002BBE4` | `0x03BE4` | Internal handler |
| 4 | `0x8002BBF0` | `0x03BF0` | Internal handler |
| 5 | `0x8002BBFC` | `0x03BFC` | Internal handler |

These are secondary entry points used by the main executable to call specific SMITH.BIN operations.

### Code Cross-References

LUI/ADDIU pair analysis reveals 138 total references from code to data:
- **59 references** to other code functions (internal calls)
- **79 references** to the BSS/data island region (`0x14500`+), used as runtime variable storage

The code does NOT directly reference the text region at `0x774C` via LUI/ADDIU pairs. Instead, text is accessed indirectly through the pointer tables and sequential string scanning.

## Data Tables (0x06300 - 0x0774B)

### Item Header Records (0x6300 - 0x639F)

8 records of 20 bytes each, containing item identifiers and sequential counters:

| Record | Offset | Item ID | Counter | Purpose |
|--------|--------|---------|---------|---------|
| 0 | `0x6300` | `0x0669` | 1 | Category/group definitions |
| 1 | `0x6314` | `0x066A` | 2 | for the smithing system |
| 2 | `0x6328` | `0x066B` | 3 | (item group IDs |
| 3 | `0x633C` | `0x066C` | 4 | map to craftable |
| 4 | `0x6350` | `0x066D` | 5 | weapon/armor |
| 5 | `0x6364` | `0x066E` | 6 | categories) |
| 6 | `0x6378` | `0x066F` | 7 | |
| 7 | `0x638C` | `0x021C` | 8 | Special item (different ID range) |

### RAM Pointer Table (0x63A0 - 0x63BF)

8 RAM addresses pointing to code functions in the `0x4300` range (file offsets `0x4300`-`0x438C`):

```
[0] 0x8002C300 -> file 0x04300
[1] 0x8002C314 -> file 0x04314
[2] 0x8002C328 -> file 0x04328
[3] 0x8002C33C -> file 0x0433C
[4] 0x8002C350 -> file 0x04350
[5] 0x8002C364 -> file 0x04364
[6] 0x8002C378 -> file 0x04378
[7] 0x8002C38C -> file 0x0438C
```

These correspond to the 8 item header records and likely define per-category initialization or validation functions.

### Recipe/Crafting Data (0x63C0 - 0x645F)

160 bytes of packed byte arrays containing item crafting recipes. The data contains small values and references to item IDs (e.g., `0x0670`-`0x067F` range), defining which ingredients combine to produce which items in the smithing system.

### Configuration Table (0x6460 - 0x6557)

248 bytes of structured parameter data. The first entry at `0x6460` begins with a RAM pointer (`0x8003C684`) and an `0xFFFF` sentinel, followed by 16-bit parameter values:

```
0x6460: 00 00 00 00 84 C6 03 80 FF FF 03 00 00 00 10 00
0x6470: 20 00 0B 00 04 00 08 00 08 00 1E 00 0F 00 12 00
```

These control smithing/UI parameters such as menu dimensions, grid sizes, and layout offsets.

### Text Line Pointer Table A (0x6558 - 0x6853)

191 x 4-byte file offsets pointing to text line positions within the description text region. All values fall within `0x0A2DC`-`0x0A9F8` (deep within the text region).

These are **text wrapping line pointers** -- they mark where each wrapped line begins within a multi-line item description, enabling the text renderer to quickly jump to specific lines when displaying paginated descriptions.

Example: The first few entries point to successive line-break positions within a single weapon description:

| Entry | File Offset | Text Fragment |
|-------|-------------|---------------|
| 0 | `0x0A2DC` | 武器の中でも非常に高い完成度を誇る。一点の曇りもない... |
| 1 | `0x0A2E8` | ...に高い完成度を誇る。一点の曇りもない完全な黒が... |
| 2 | `0x0A2F2` | ...を誇る。一点の曇りもない完全な黒が闇に溶け込む... |
| 3 | `0x0A2FE` | ...りもない完全な黒が闇に溶け込む時そこは死体の山と... |

### Code Function Pointer Table (0x6854 - 0x6FFF)

491 x 4-byte file offsets pointing to MIPS functions within the code region (`0x0708`-`0x4C00`). These are **item effect handler function pointers** -- each entry maps to a function that implements a specific item's use/equip/effect logic.

All 491 entries point to valid code region addresses.

### Data Offset Table (0x7000 - 0x728F)

164 x 4-byte file offsets pointing to binary data records in the code/data region (`0x4C54`-`0x6FE2`). These offsets reference **item property/stat data structures** embedded within or adjacent to the code. The values are monotonically increasing, suggesting they index sequential records of variable size.

### Text Line Pointer Table B (0x7290 - 0x774B)

303 x 4-byte file offsets. The values range from `0x0702C` to `0x0A2C4`:

- **26 entries** point to the data offset table region (`0x7000`-`0x7290`)
- **277 entries** point to the text description region (`0x774C`+)
- **113 duplicate values** (entries sharing the same offset)
- The table is **not strictly sorted**

These function similarly to Table A as text line position references, but cover the earlier portion of the text region. The first 26 entries referencing the data offset table likely serve as indirect references for items with complex multi-part descriptions.

## Item Description Text (0x0774C - 0x10F31)

### Overview

| Property | Value |
|----------|-------|
| Total strings | 628 |
| Region size | 38,886 bytes |
| First string | `0x0774C` |
| Last string | `0x10F2A` |
| Encoding | Standard game text (see `TEXT_ENCODING.md`) |

The 628 description strings are stored as null-terminated sequences, tightly packed with occasional 1-byte alignment gaps between strings (295 gaps of 1 byte each).

### String Access Method

The text descriptions are accessed **sequentially by item index** -- item 0 corresponds to the first null-terminated string, item 1 to the second, and so on. The code scans forward through null terminators to reach the Nth description. The pointer tables at `0x6558` and `0x7290` provide pre-computed line break positions for text wrapping during rendering, not string start positions.

### Content Categories

The 628 descriptions cover all equippable and usable items in the game. Content is arranged roughly by equipment type:

| Category | Keyword Detection | Sample String Range | Notable Content |
|----------|-------------------|-------------------|-----------------|
| **Swords** (剣) | 59 matches | strings 1-389 | Elemental swords (地/水/火/風/光), legendary blades, basic to mythical |
| **Katanas** (刀) | 29 matches | strings 33-39+ | Eastern-style blades, craftsman Amakuni's works |
| **Daggers** (短剣) | 30 matches | strings 91-205 | Short blades, assassin weapons |
| **Axes** (斧) | 16 matches | strings 59-408 | Heavy weapons |
| **Spears** (槍) | 18 matches | strings 121-360 | Polearms, lances |
| **Clubs** (棍棒) | 25 matches | strings 50-332 | Blunt weapons, maces, hammers |
| **Staves** (杖/ロッド) | 19 matches | strings 126-175 | Magic-user weapons |
| **Gloves** (拳) | 21 matches | strings 6-529 | Gauntlets, fist weapons |
| **Bows** (弓) | — | scattered | Ranged weapons |
| **Cards** (カード) | 11 matches | strings 280-464 | Magic cards with elemental properties |
| **Armor** (鎧) | 31 matches | strings 112-347 | Body armor, robes |
| **Shields** (盾) | 5 matches | strings 336-362 | Defensive equipment |
| **Helmets** (兜) | 2 matches | strings 409-417 | Head protection |
| **Boots** (靴) | 16 matches | strings 193-411 | Footwear |
| **Accessories** | 14 matches | strings 308-465 | Rings, necklaces, bracelets |
| **[opt] prefix** | 32 strings | strings 596-621 | Menu option labels ("...を設定する", "...を回復する") |
| **Effect text** | 33 strings | strings 622-627+ | "ダメージを与える", status recovery |

Note: Categories overlap because keyword detection is approximate. Many descriptions contain multiple equipment-type keywords when comparing items or describing hybrid weapons.

### Sample Decoded Text

| # | Offset | Description |
|---|--------|-------------|
| 0 | `0x0774C` | 使っても無くならず、何度でもぶつけられる。 |
| 1 | `0x07766` | 普通の剣。剣士を志すものはまずこれを使いこなすことから始める。 |
| 2 | `0x0778E` | 小さく軽いが、戦闘用の剣ではなく、威力は大したことがない。この程度の剣で戦いに望むべきではない。 |
| 3 | `0x077CE` | 三日月のかたちをした刃が美しい剣。この刀身の形は斬り合いに非常に適している。 |
| 9 | `0x07938` | 地の精霊の力が衰えたときに現れると言われる力の象徴。地の精霊の力が宿っており、心あるものがこの剣を振るうことで本当の力が発揮できるとされる。 |
| 10 | `0x07994` | 水の精霊の力が衰えたときに現れると言われる力の象徴。... |
| 11 | `0x079F0` | 火の精霊の力が衰えたときに現れると言われる力の象徴。... |
| 12 | `0x07A4C` | 風の精霊の力が衰えたときに現れると言われる力の象徴。... |
| 13 | `0x07AA8` | 光の精霊の力が衰えたときに現れると言われる力の象徴。... |
| 33 | `0x08114` | 片刃の刀身の長い独特の形をした剣。刃とみねを使い分けることで、無用の殺生をさけることができる。 |
| 36 | `0x081FE` | 刀。「斬る」よりも「引く」ことをイメージして使う。海を越えはるか東の国の刀鍛冶アマクニによってつくられた。... |
| 623 | `0x10EE2` | 全てのステータス異常を回復する |
| 624 | `0x10EF8` | ダメージを与える |
| 627 | `0x10F2A` | うつせみの玉 |

Descriptions range from short effect labels (8 bytes) to detailed weapon lore (114 bytes), with an average of ~62 bytes per string.

### Elemental Sword Series

Five elemental swords form a notable set (strings 9-13), each following the same template:

> [Element]の精霊の力が衰えたときに現れると言われる力の象徴。[Element]の精霊の力が宿っており、心あるものがこの剣を振るうことで本当の力が発揮できるとされる。

Elements: 地 (Earth), 水 (Water), 火 (Fire), 風 (Wind), 光 (Light)

## BSS Region (0x10F32 - 0x164FF)

21,966 bytes of all-zero data in the file. At runtime, this region (RAM `0x8003CF32`+) is used for dynamically-allocated variables. Code LUI/ADDIU pairs reference addresses in this range (e.g., `0x8003C558`, `0x8003C5E4`) as runtime buffers for item calculations, inventory state, and temporary storage.

This is functionally equivalent to a `.bss` section in a standard executable format.

## Secondary Data Island (0x16500 - 0x1663E)

319 bytes of initialized data at the end of the active region, separated from the main data by the BSS zero region.

### Structure

| Sub-Offset | Content |
|------------|---------|
| `0x16500`-`0x16557` | 88 bytes of zero padding (alignment) |
| `0x16558`-`0x1657B` | **Cross-module function pointers** -- 9 RAM addresses using base `0x80026000` (SDIC.BIN's load address) |
| `0x16580`-`0x165E3` | **Parameter blocks** -- Groups of 16-bit key-value pairs terminated by `0xFFFF` sentinels |
| `0x165E4`-`0x165EF` | 3 RAM pointers (`0x8003C57C`, `0x8003C594`, `0x8003C5B0`) to BSS region |
| `0x165F0`-`0x1663E` | Smithing UI configuration data (layout parameters, item type flags) |

### Cross-Module Function Pointers (0x16558)

Nine RAM addresses use SDIC.BIN's base address (`0x80026000`), not SMITH.BIN's (`0x80028000`):

| Index | RAM Address | SDIC.BIN Offset | Purpose |
|-------|------------|-----------------|---------|
| 0 | `0x800261C0` | `0x001C0` | Cross-module callback |
| 1 | `0x80028294` | `0x00294` (SMITH.BIN) | Local handler |
| 2 | `0x800262B4` | `0x002B4` | Cross-module callback |
| 3 | `0x800267B8` | `0x007B8` | Cross-module callback |
| 4 | `0x80027908` | `0x01908` | Cross-module callback |
| 5 | `0x80027D74` | `0x01D74` | Cross-module callback |
| 6 | `0x80026E48` | `0x00E48` | Cross-module callback |
| 7 | `0x80027374` | `0x01374` | Cross-module callback |
| 8 | `0x8002628C` | `0x0028C` | Cross-module callback |

This cross-module reference table allows SMITH.BIN's item system to invoke SDIC.BIN's text rendering functions (e.g., `render_char`, `render_string`) when displaying item descriptions.

### Parameter Blocks (0x16580)

Three groups of 16-bit key-value pairs, each terminated by `0xFFFF`:

**Block 1** (4 entries):
```
{key=0x0000, val=0x0001},  // Type: 1
{key=0x00C8, val=0x0002},  // Cost: 200 GP
{key=0x1F40, val=0x0003},  // Cost: 8000 GP
{key=0x0000, val=0x0007},  // Category: 7
0xFFFF                      // Terminator
```

**Block 2** (7 entries): Additional crafting parameters
**Block 3** (8 entries): Full category parameter set

## Text Encoding

Text strings in SMITH.BIN use the same encoding as all other game files (see `TEXT_ENCODING.md`):

| Byte Range | Encoding | CharID Range |
|------------|----------|--------------|
| `0x00` | Null terminator | -- |
| `0x01`-`0xEE` | Single byte | 1-238 |
| `0xEF` | Choice option prefix | -- |
| `0xF0 XX`-`0xF5 XX` | Two bytes | 239-1768 |
| `0xFF sub p1 p2` | Control code | -- |

The `[opt]` (0xEF) prefix appears in 32 strings near the end of the text region, marking selectable menu options for item use/configuration screens.

## Comparison with SDIC.BIN

| Property | SDIC.BIN | SMITH.BIN |
|----------|----------|-----------|
| Load address | `0x80026000` | `0x80028000` |
| File size | 102,400 bytes | 102,400 bytes |
| Code size | 16,400 bytes (21 functions) | 25,208 bytes (108 functions) |
| Text entries | 555 | 628 |
| Text size | 14,148 bytes | 38,886 bytes |
| Text content | Character profiles, monster encyclopedia | Item/equipment descriptions |
| Pointer table | Two-level (table-relative offsets) | Line-position pointers (direct file offsets) |
| Active data | 38.9% | 68.0% |
| Entry point | Jump table with function offsets | Jump table with RAM addresses |
| Cross-module refs | None | 9 refs to SDIC.BIN (text rendering) |

## Relevance to Korean Translation

### Text that needs translation

SMITH.BIN contains **628 translatable text entries** totaling ~38,886 raw bytes:

1. **~560 item/equipment descriptions**: Detailed lore and stat descriptions for every weapon, armor, accessory, and special item in the game
2. **32 menu option labels**: Short strings with `[opt]` prefix for item use/configuration menus (e.g., "...を設定する", "...を回復する")
3. **~36 effect/status strings**: Short labels like "ダメージを与える" (deals damage), "全てのステータス異常を回復する" (recovers all status ailments)

### Modification approach

For translation, the text region at `0x0774C`-`0x10F31` can be modified in-place:

1. **Replace description strings**: Translate each null-terminated string, keeping null terminators
2. **Update text line pointer tables**: Both Table A (`0x6558`, 191 entries) and Table B (`0x7290`, 303 entries) contain pre-computed line break positions that must be recalculated after translation to match the new text layout
3. **Adjust sequential string boundaries**: Since the code accesses descriptions by sequential index, string lengths can change freely as long as null terminators are preserved

### Available space

The BSS region (`0x10F32`-`0x164FF`, 21,966 bytes) can potentially be reclaimed for text expansion if needed, though care must be taken since the code uses this area for runtime variables. The safer expansion space is the final zero padding (`0x1663F`-`0x18FFF`, 10,689 bytes). Combined with the existing 38,886-byte text region, there is room for modest text expansion.

Korean translations are typically comparable in byte-length to Japanese for this encoding, so the existing text region should be sufficient in most cases.

### Dependencies

| File | Role |
|------|------|
| `SMITH.BIN` | Item code + descriptions (this file) |
| `SDIC.BIN` | Text rendering functions (called via cross-module pointers) |
| `COMM.IMG` | Font texture (character glyphs) |
| `SCPS_100.26` | Main executable: item database, control code dispatcher |
| `S*.STG` | Stage data (may reference item IDs) |
