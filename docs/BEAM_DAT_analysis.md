# BEAM.DAT Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `BEAM.DAT` |
| Size | 35,553,280 bytes (33.9 MB, 0x21E8000) |
| Sectors | 17,360 CD-ROM sectors (2,048 bytes each) |
| Type | Composite archive -- battle effects data + embedded PS-X executable |
| Contains text | **Yes** -- battle dialogue, system messages, name/location tables |

## Purpose

BEAM.DAT is the game's **battle effects archive**. The name "BEAM" refers to the in-game beam attacks, magic spells, and visual effects used during battle sequences. The file bundles:

- Sprite textures and palettes for spell/beam visual effects
- Small MIPS overlay stubs that initialize each effect at runtime
- Battle scene dialogue and system message text
- A **complete embedded PS-X executable** (the battle engine, distinct from `SCPS_100.26`)

## Archive Structure

The file consists of **46 fixed-size entries** of 772,096 bytes (0xBC800, 377 CD-ROM sectors) each, plus a 36,864-byte (0x9000) tail section:

```
46 × 0xBC800 + 0x9000 = 0x21E8000  (35,553,280 bytes -- exact match)
```

There is **no table of contents** -- the game engine accesses entries by computing `entry_index × 0xBC800`.

### Entry Layout

| Zone | Entries | File Offset | Size | Description |
|------|---------|-------------|------|-------------|
| A | 0-4 | `0x000000`-`0x3AE7FF` | 3.7 MB | Graphics data (shared texture atlases, palettes) |
| B | 5-43 | `0x3AE800`-`0x2065FFF` | 30.1 MB | Battle effect entries (graphics + MIPS stubs + text) |
| C | 44-45 | `0x2066000`-`0x21DEFFF` | 1.5 MB | **Embedded PS-X executable** (battle engine) |
| D | Tail | `0x21DF000`-`0x21E7FFF` | 36 KB | Additional sprite/texture data |

## Zone A: Graphics Data (Entries 0-4)

Five entries of pure PS1 pixel data. No MIPS code or text.

- Contains 15-bit ABGR1555 color palettes and 4bpp/8bpp indexed textures
- Entry 0 starts with a 16-color CLUT including the PS1 standard magenta transparency key (`0x7C1F`)
- Each entry has unique content -- likely shared texture atlases for common spell effects

## Zone B: Battle Effect Entries (Entries 5-43)

39 entries, each containing a self-contained battle effect package:

### Internal Layout (per entry)

| Offset | Size | Content |
|--------|------|---------|
| `+0x00000` | ~696 KB | Sprite/animation graphics data |
| `+0x24000`-`+0x32000` | ~57 KB | Zero-filled reserved region |
| `+0x30000`-`+0x36000` | ~24 KB | **Embedded game text** (dialogue, system messages) |
| `+0xAE000` | ~1 KB | MIPS overlay stub A (effect initializer) |
| `+0xB7000` | ~1.2 KB | MIPS overlay stub B (effect handler) |
| `+0xBA000`-`+0xBC7FF` | ~10 KB | Additional data + zero padding |

### MIPS Overlay Stubs

Each entry contains two small MIPS R3000 code stubs loaded as runtime overlays:

**Stub A** (+0xAE000): Effect initialization
```mips
addiu $sp, $sp, -24      ; function prologue
sw    $ra, 16($sp)
jal   0x00077820          ; call effect init routine
nop
lw    $ra, 16($sp)
addiu $sp, $sp, 24
jr    $ra                 ; return
```

**Stub B** (+0xB7000): Effect handler with GP setup
```mips
lui   $gp, 0x8007        ; set global pointer
addiu $gp, $gp, 0x7954   ; GP = 0x80077954
j     0x00077800          ; jump to effect handler
```

The stubs reference RAM addresses for effect parameter structures and VRAM upload coordinates. They are loaded at runtime to manage spell/beam rendering.

### Text in Effect Entries

Entries 6-43 embed game text at approximately +0x030000 within each entry. The text uses the same encoding as all other game files (single-byte 0x01-0xEE, two-byte 0xF0-0xF5+XX, FF control codes).

**Unique dialogue** is concentrated in the first few effect entries:

| Entry | File Offset | Content |
|-------|-------------|---------|
| 6 | `0x046B000`+0x030000 | Choko story dialogue, system messages |
| 7 | `0x0527800`+0x030000 | Gogen story dialogue |
| 8 | `0x05E4000`+0x030000 | Lieza/Riza story dialogue |
| 9 | `0x06A0800`+0x030000 | Additional Choko dialogue |
| 10 | `0x075D000`+0x030000 | Additional scene dialogue |

**Entries 11-43 (33 entries)** share a common template of system messages and battle dialogue, duplicated at ~0xBC800-byte intervals. These include:

- Switch/treasure interaction prompts ("スイッチがあります　ONにしてみますか？")
- Item found messages ("アイテムを見つけました　取りますか？")
- Item box full warnings ("アイテムBOXがいっぱいです")
- Yes/no choice prompts (はい/いいえ)
- Character speech and narration

The 33-fold duplication means each battle scenario carries its own copy of the shared message library.

## Zone C: Embedded PS-X Executable (Entries 44-45)

A complete PS1 executable is embedded at file offset `0x209D000`, distinct from the disc's boot executable `SCPS_100.26`.

### PS-X EXE Header

| Field | Value | SCPS_100.26 (comparison) |
|-------|-------|--------------------------|
| Magic | `PS-X EXE` | `PS-X EXE` |
| Entry point | `0x80164804` | `0x80167E1C` |
| Load address | `0x800C1400` | `0x800C1400` |
| Code size | `0x0DA800` (894,976 bytes) | `0x0DD800` (907,264 bytes) |
| SP | `0x801FFFF0` | `0x801FFFF0` |
| Region | Japan | Japan |

### Comparison with SCPS_100.26

| Property | BEAM.DAT EXE | SCPS_100.26 |
|----------|-------------|-------------|
| Size | 894,976 bytes (874 KB) | 907,264 bytes (886 KB) |
| Entry point | `0x80164804` | `0x80167E1C` |
| RAM range | `0x800C1400`-`0x8019BC00` | `0x800C1400`-`0x8019EC00` |
| Byte identity | 12.7% identical | -- |

The two executables load to the **same RAM address** (`0x800C1400`) but are only **12.7% byte-identical** -- they are separate builds. The BEAM.DAT EXE is 12 KB smaller and has a different entry point. This is the **battle engine executable** that replaces `SCPS_100.26` in memory when the game enters battle mode.

The entry point at `0x80164804` clears BSS from `0x801AB978` to `0x8020AC3C` (a larger BSS region than SCPS_100.26's `0x8019E850`-`0x801FC834`).

### Debug Strings

The embedded EXE contains Sony PS1 SDK library debug strings:

| Category | Examples |
|----------|---------|
| CD-ROM | `CdInit: Init failed`, `CdSearchFile: searching %s...` |
| GPU/DMA | `GPU timeout`, `DMA bus error: code=%08x` |
| Sound | `SsVabOpenHead : error`, `PLAYMUS:VAB`, `PLAYMUS:BGM` |
| Game logic | `prmSetNo Error!! %d`, `statTurnGet Error!!`, `MAGIC SE ERR %d`, `dmg type err` |

### File References

The embedded EXE references these disc files by name:

```
YCHO.BIN, YSEG.BIN, SDIC.BIN, SMITH.BIN, YPROP.BIN, YGUILD.BIN, YSHOP.BIN
COMM.SND, COMM.DAT, COMM.IMG
```

Notable: **`YCHO.BIN`** appears here but is not present on the disc as a standalone file. It may be an earlier development name for one of the existing overlays, or an overlay embedded within BEAM.DAT itself.

The EXE also contains disc identifiers for both games:
- `BISCPS-10008ARC1-00` (Arc the Lad 1)
- `BISCPS-10026ARC2-00` (Arc the Lad 2)

### Text Data in Embedded EXE

The embedded EXE contains master data tables in its data region:

| File Offset | RAM Address | Content |
|-------------|-------------|---------|
| `0x0216C720` | `0x80190320` | Character name table (~12 names) |
| `0x0216C86C` | `0x8019046C` | Monster name table (~150+ names) |
| `0x0216D03E` | `0x80190C3E` | Skill/technique name table (~50+ names) |
| `0x0216D5D0` | `0x801911D0` | Save/load system messages (~20 strings) |
| `0x02170800` | `0x80194400` | Location/map name table (~80+ names) |
| `0x021716D0` | `0x801952D0` | Movie/cutscene name table (24 entries) |

These tables are structurally similar to the equivalent tables in SCPS_100.26 but are a separate copy maintained within the battle engine.

## Zone D: Tail Graphics (0x21DF000-0x21E7FFF)

36,864 bytes of additional PS1 sprite/texture data (4bpp and 8bpp indexed pixels). No text or code. Last non-zero byte at `0x21E7EFF`, followed by 256 bytes of zero padding to the sector boundary.

## Text Content Summary

### Distribution

Text in BEAM.DAT exists in two distinct locations:

1. **Effect entries (Zone B)**: Battle dialogue and system messages embedded per-entry at +0x030000. Heavily duplicated across 33 entries, with unique story dialogue in entries 6-10.

2. **Embedded PS-X EXE (Zone C)**: Master name/data tables (characters, monsters, locations, skills, save/load UI, movie titles).

### Estimated Unique Strings

| Category | Count | Location |
|----------|-------|----------|
| System/UI messages | ~50-80 | Effect entries (shared template) |
| Character names | ~12 | EXE data (0x0216C720) |
| Monster names | ~150 | EXE data (0x0216C86C) |
| Skill/technique names | ~50 | EXE data (0x0216D03E) |
| Save/load messages | ~20 | EXE data (0x0216D5D0) |
| Location/map names | ~80 | EXE data (0x02170800) |
| Movie names | 24 | EXE data (0x021716D0) |
| Unique story dialogue | ~500-1,000 | Effect entries 6-10 |
| **Total estimated unique** | **~900-1,400** | |

Many of the name/data table strings overlap with SCPS_100.26's equivalent tables. The unique content is primarily the battle scene dialogue in effect entries 6-10.

### Encoding Notes

The text decoder shows some kanji inaccuracies in BEAM.DAT strings (e.g., "協つけました" instead of "見つけました"). This may indicate:
- The BEAM.DAT EXE uses a slightly different charID-to-glyph mapping than SCPS_100.26
- Or the character table used by the decoder has inaccuracies for some kanji ranges

The kana (hiragana/katakana) and control codes decode correctly across both executables.

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **SCPS_100.26** | Main executable (overworld/menu). Replaced in memory by BEAM.DAT's embedded EXE during battle. Both load to `0x800C1400`. |
| **COMM.IMG** | Font texture -- referenced by BEAM.DAT's EXE for text rendering |
| **COMM.DAT** | Battle animation module -- loaded alongside BEAM.DAT's EXE at `0x80010000` |
| **COMM.SND** | Sound bank -- loaded by BEAM.DAT's EXE for battle SFX |
| **SDIC.BIN** | Dialogue controller -- loaded by BEAM.DAT's EXE at `0x80026000` |
| **SMITH.BIN** | Item system -- loaded at `0x80028000` during battle |
| **S*.STG** | Stage files provide the battle map data; BEAM.DAT provides the battle effects |

## Relevance to Korean Translation

### What Needs Translation

1. **Effect entry text** (entries 6-43): Battle dialogue and system prompts. The shared template (~50-80 unique strings) is duplicated 33 times and must be patched in every copy. Unique story dialogue in entries 6-10 (~500-1,000 strings) needs individual translation.

2. **Embedded EXE data tables** (0x0216C720-0x02171900): Character names, monster names, location names, skill names, save/load messages, movie names. These are separate copies from SCPS_100.26 and must be translated independently.

### Challenges

- **Large file size** (33.9 MB): Patching requires careful offset management across the 46-entry archive structure.
- **33-fold duplication**: System message changes must be applied to all 33 copies in entries 11-43, plus unique copies in entries 6-10.
- **Separate executable**: The embedded EXE may have different SJIS mapping tables or charID assignments than SCPS_100.26. The Korean character mapping must be validated against both executables.
- **Fixed entry size**: Each entry is exactly 0xBC800 bytes. Translated text must fit within the existing space allocated per entry.

### What Does NOT Need Modification

- Zone A graphics entries (0-4) -- pure pixel data, no text
- MIPS overlay stubs -- language-agnostic effect initialization code
- Zone D tail graphics -- pure pixel data
- Archive structure -- no TOC to update, entries are accessed by fixed stride
