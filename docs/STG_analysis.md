# S*.STG Stage File Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| Files | 19 stage files: `S100.STG` through `SJ00.STG` |
| Total size | ~306 MB across all 19 files |
| Type | Composite stage archives -- scene data with graphics, audio, code, and dialogue |
| Chunk size | 772,096 bytes (0xBC800 = 377 CD-ROM sectors) per chunk |
| Contains text | **Yes** -- 19,568 dialogue strings total across all STG files |

### All STG Files

| File | Size | Chunks | Dialogues | Notes |
|------|------|--------|-----------|-------|
| S100.STG | 8.1 MB | 11 | 1,164 | Prodias (Aldia capital, opening chapter) |
| S200.STG | 12.5 MB | 17 | 1,754 | |
| S300.STG | 8.1 MB | 11 | 320 | |
| S400.STG | 7.4 MB | 10 | 778 | |
| S500.STG | 8.8 MB | 12 | 526 | |
| S600.STG | 11.8 MB | 16 | 753 | |
| S700.STG | 25.0 MB | 34 | 2,549 | |
| S800.STG | 11.8 MB | 16 | 931 | |
| S900.STG | 10.3 MB | 14 | 921 | |
| SA00.STG | 11.0 MB | 15 | 1,269 | |
| SB00.STG | 7.4 MB | 10 | 775 | |
| SC00.STG | 14.7 MB | 20 | 702 | |
| SD00.STG | 13.3 MB | 18 | 661 | |
| SE00.STG | 14.7 MB | 20 | 1,213 | |
| SF00.STG | 34.6 MB | 47 | 2,499 | |
| SG00.STG | 41.2 MB | 56 | 1,492 | |
| SH00.STG | 11.8 MB | 16 | 49 | Minimal dialogue (cutscene-heavy?) |
| SI00.STG | 28.7 MB | 39 | 2,122 | |
| SJ00.STG | 0.1 MB | 0* | 0 | Special (header-only, no chunks) |
| **Total** | **306 MB** | **377** | **19,478** | |

*SJ00.STG (81,920 bytes = 40 sectors) does not follow the chunk structure -- it is smaller than one chunk and may be a header-only file or special stage data.

Every STG file size (except SJ00) is an **exact multiple of 0xBC800** (772,096 bytes). This is the same chunk size used by `BEAM.DAT`, confirming a unified archive format across the game's stage and battle effect files.

## Archive Structure

Each STG file consists of N fixed-size chunks of 772,096 bytes, with no table of contents. The game engine accesses chunks by computing `chunk_index × 0xBC800`.

```
S100.STG (8,493,056 bytes)
 = 11 chunks × 772,096 bytes
 = 11 chunks × 377 sectors

Each chunk = one scene/event within the stage
```

## Chunk Internal Layout

Every chunk follows a consistent internal layout with the following sections:

| Chunk Offset | Size | Content |
|-------------|------|---------|
| `+0x00000` | ~32 KB | 4bpp tile/sprite pixel data |
| `+0x08000` | ~96 KB | Tile map layers (base, overlay, shadow) |
| `+0x20000` | ~96 KB | Extended graphics data (additional tiles, color variants) |
| `+0x38000` | ~32 KB | Sprite/character graphics (4bpp with transparency padding) |
| `+0x40000` | ~12 KB | **VAB sound banks** (2 per chunk, `pBAV` magic, version 7) |
| `+0x43000` | ~28 KB | **SEQ music sequences** (`pQES` magic, 1-5 per chunk) |
| `+0x4A000` | ~155 KB | ADPCM audio samples (VAG format, 16-byte blocks) |
| `+0x70000` | ~64 KB | Zero padding / reserved |
| `+0x80000` | ~16 KB | **MIPS R3000A overlay code** (small effect/scene handler) |
| `+0x84000` | ~48 KB | Texture/portrait data (VRAM upload) |
| `+0x90000` | ~144 KB | Event data tables, animation data, coordinate tables |
| `+0xB4000` | ~34 KB | **Event script bytecode with inline dialogue text** |

### Section Details

#### Graphics (0x00000-0x3FFFF)

The first ~256 KB of each chunk contains tile and sprite graphics in PS1 4bpp indexed format:

- **Tile pixel data** (+0x00000): Raw 4-bit indexed pixels for map tiles. Low nibble = left pixel, high nibble = right pixel.
- **Tile maps** (+0x08000): Layer definitions using tile indices. Multiple layers for base terrain, overlays, and shadows. Includes solid-color fill tiles (repeated bytes like 0x22, 0xDD, 0xFF).
- **Extended graphics** (+0x20000): Additional tile sets and color variations.
- **Sprites** (+0x38000): Character and object sprite sheets, 4bpp with zero-padded transparency regions.

#### Audio (0x40000-0x6FFFF)

Each chunk embeds its own audio resources:

- **2 VAB sound banks** (`pBAV` header, version 7, ID 0): Instrument definitions and sample parameters for the scene's sound effects and music.
- **1-5 SEQ music sequences** (`pQES` header, version 0): MIDI-like music data played through the VAB instruments.
- **ADPCM audio samples** (VAG format): Compressed audio waveforms in 16-byte blocks (4-bit ADPCM, ~3.5:1 compression ratio). ~155 KB per chunk.

#### MIPS Code (0x80000-0x83FFF)

A small (~2-4 KB) PS1 MIPS R3000A overlay loaded at runtime:

```mips
+0x80000: addiu $sp, $sp, -24      ; function prologue
+0x80004: sw    $ra, 20($sp)
+0x80008: sw    $s8, 16($sp)
          ...
          lui   $gp, 0x8008         ; GP → 0x80082F74 (chunk-specific)
          addiu $gp, $gp, 0x2F74
```

Each chunk's overlay has a unique GP value, confirming chunks are loaded independently. The code contains a jump table of RAM pointers (0x80081xxx-0x80083xxx range) for scene-specific logic (trigger handlers, entity behaviors, camera control).

#### Event Script + Dialogue (0xB4000-0xBC7FF)

The final ~34 KB of each chunk contains the **event script bytecode** with inline dialogue text. This is the primary target for translation.

## Event Script Format

### Script Bytecode

The event script is a bytecode stream that controls dialogue flow, scene transitions, and game events. Key opcodes:

| Opcode | Pattern | Meaning |
|--------|---------|---------|
| `23 01` | Before `F0 8B` | Text block end marker |
| `F0 8B` | `F0 8B [speaker_2b]` | Display text command (with speaker ID) |
| `28 01` | `28 01 [params]` | Parameter block (10 bytes each) |
| `45 01` | Between F0 8B pairs | Display text variant separator |
| `63 00` | After second F0 0B | Command end / fallthrough |
| `A2 00` | `A2 00 [offset] [flag]` | Jump to script offset |
| `A9 00` | `A9 00 [target]` | Conditional branch |
| `2D 00 30 00 62 00 02 80` | After text blocks | Standard command postamble |
| `FF FF` | Block terminator | Section delimiter |

### Dialogue Display Sequence

A complete dialogue display follows this pattern:

```
[encoded_text_bytes] 00        ← Null-terminated text string
[2-byte script offset]         ← Event script address
23 01                           ← Text block end marker
F0 8B [speaker] 28 01          ← Display command (speaker ID)
F0 0B 04 00 00 80 [target_A]   ← Wait + branch option A
45 01                           ← Separator
F0 8B [speaker] 28 01          ← Duplicate display command
F0 0B 00 00 00 80 [target_B]   ← Branch option B
63 00 [speaker] [fallback]      ← Command end
2D 00 30 00 62 00 02 80 A9 00  ← Postamble
```

The 48-byte template structure between dialogue strings (documented in `TEXT_ENCODING.md`) mirrors this pattern exactly -- positions +0..+15 and +16..+31 are the two parallel F0 8B/F0 0B display command pairs.

### Speaker IDs

The 2-byte speaker ID at offset +2 of the `F0 8B` command identifies who is speaking:

| Speaker ID | Observed Usage |
|-----------|----------------|
| `0xFFFE` | Generic NPC / narrator |
| `0x8005` | Elk (protagonist) |
| `0x8006` | Lieza |
| `0x8000` | Default / system |
| `0x8001` | Primary dialogue context |
| `0x8009` | NPC group |
| `0x800A`-`0x800E` | Various characters |

When the speaker ID changes between consecutive templates, additional script bytes (scene setup commands) appear at the transition point.

### Text Encoding

Dialogue text within the event script uses the game's standard encoding (see `TEXT_ENCODING.md`):

| Byte Range | Encoding |
|-----------|----------|
| `0x00` | Null terminator |
| `0x01`-`0xEE` | Single-byte charID (hiragana, katakana, Latin, digits, symbols) |
| `0xEF` | Choice option prefix |
| `0xF0 XX`-`0xF5 XX` | Two-byte charID (kanji, extended characters) |
| `0xFF XX XX XX` | Control codes (newline, dialogue box, delay, etc.) |

## S100.STG Text Content

### Statistics

| Property | Value |
|----------|-------|
| STG dialogue strings | 1,164 |
| Offset range | `0x000B4516` -- `0x0075BD2A` |
| Text encoding | Game custom (same as all other files) |
| Chunks containing text | All 11 |

### Content Summary

S100.STG covers the game's opening chapter in **Prodias** (the capital of Aldia):

**Town exploration:**
- NPC dialogue about Romalia, Gallarno, and city life
- Elk's apartment and neighborhood interactions
- Guild conversations and mission briefings

```
0x000B4516: 大きな街ね                    (What a big city)
0x000B45C8: ここが、俺のアパートだ          (This is my apartment)
0x000B48CC: ロマリアばんらーい              (Long live Romalia!)
```

**Character interactions:**
- Town NPCs greeting Elk by name
- Lieza and Elk dialogue
- Guild members recognizing Elk as "the fire user"

```
0x000B5022: よう、エルクじゃねえか          (Hey, isn't that Elk?)
0x000B68FA: ロマリア、ガルアーノ、女神像    (Romalia, Gallarno, the Goddess Statue)
```

**Dramatic ceremony and airship attack:**
- Goddess Statue ceremony at the city center
- Characters losing consciousness
- Airship attack and Elk's village flashback

```
0x0075B16C: その美しい姿をお目にかけましょう！  (Let us show you its beautiful form!)
0x0075B446: 飛行船だ！                          (It's an airship!)
0x0075BAB6: 俺の・・俺の村を襲った…              (My... it attacked my village...)
0x0075BC72: ゆるさねぇ！                         (I won't forgive them!)
```

## Shared Architecture with BEAM.DAT

STG files and BEAM.DAT use the **same 0xBC800-byte chunk format**. Key similarities:

| Property | STG Files | BEAM.DAT |
|----------|-----------|----------|
| Chunk size | 0xBC800 (772,096 bytes) | 0xBC800 (772,096 bytes) |
| Graphics at +0x00000 | Map tiles, sprites | Spell/beam textures |
| Audio at +0x40000 | Scene music/SFX | Battle SFX |
| MIPS code at +0x80000 | Scene handler | Effect initializer |
| Event script at +0xB4000 | Dialogue + flow control | Battle dialogue |
| Embedded EXE | No | Yes (entries 44-45) |

The unified chunk format means the game engine has a single loader for both stage scenes and battle effects, selecting the appropriate chunk by index.

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **SCPS_100.26** | Main executable -- drives the event script engine that interprets STG bytecode |
| **BEAM.DAT** | Battle effects -- shares the 0xBC800 chunk format; loaded when battles occur within a stage |
| **COMM.IMG** | Font texture -- provides the glyphs referenced by dialogue text charIDs |
| **SDIC.BIN** | Dialogue controller -- renders the text windows displaying STG dialogue |
| **COMM.DAT** | Battle animation module -- loaded alongside battle chunks |
| **COMM.SND** | Sound bank -- supplements the per-chunk VAB banks with shared battle audio |

## Relevance to Korean Translation

### What Needs Translation

All 19,568 dialogue strings across the 19 STG files. These are the bulk of the game's story content.

### Text Location

Text is located at chunk offset `+0xB4000` through `+0xBC7FF` (~34 KB per chunk) in every chunk of every STG file. It is embedded inline within the event script bytecode, interleaved with 48-byte template blocks that control dialogue flow.

### Translation Constraints

1. **Inline encoding**: Text strings are embedded directly in the event script bytecode, not in a separate string table. Changing string lengths affects the script offset pointers in the surrounding template blocks.

2. **2-byte script prefixes**: Each dialogue string is preceded by a 2-byte little-endian script offset. These offsets increase monotonically and must be recalculated if text lengths change.

3. **48-byte template blocks**: The fixed template blocks between strings contain three 16-bit pointer fields that reference script offsets. These must be updated to match the new text positions.

4. **Fixed chunk size**: Each chunk is exactly 0xBC800 bytes. The event script region (~34 KB at +0xB4000) must accommodate all translated text without exceeding the chunk boundary.

5. **Per-chunk audio/graphics**: Each chunk is self-contained. Text changes in one chunk do not affect other chunks, but every chunk must be individually patched.

### Changing Text Length

Dialogue text is embedded **inline** within the event script bytecode. Each string has this structure:

```
[text bytes...] 00          ← Variable-length text + null terminator
[2-byte script offset]      ← Little-endian offset into script address space
[48-byte template block]    ← Contains 3 pointer fields at +14, +30, +36
[next text...]
```

**If text length changes**, all subsequent offsets shift and become invalid. The event script engine will jump to wrong addresses, causing crashes or garbage output.

#### What Must Be Updated

For every text length change within a chunk:

| Element | Location | Update Required |
|---------|----------|-----------------|
| 2-byte script prefix | Before each string | Recalculate all subsequent prefixes |
| Template pointer A | Template +14 | Recalculate (current_prefix + 0x10) |
| Template pointer B | Template +30 | Recalculate (pointer_A + 0x05) |
| Template pointer C | Template +36 | Recalculate (points to earlier dialogue) |

All three pointer fields in the 48-byte template block are **relative to the script address space**, not absolute file offsets. When text shifts, every downstream pointer must be adjusted by the delta.

#### Practical Approaches

| Approach | Difficulty | Description |
|----------|------------|-------------|
| **Fixed length** | Easy | Pad shorter translations with spaces; truncate or abbreviate longer ones |
| **Offset patcher** | Medium | Build a tool that parses all strings, recalculates all offsets, and rewrites the chunk |
| **Text relocation** | Hard | Move text to unused space within the chunk and patch all pointers to the new location |

#### Recommended Strategy

Korean text is often more compact than Japanese (no hiragana grammatical particles), so many translations will naturally fit. For strings that exceed the original length:

1. **Use shorter synonyms** where meaning is preserved
2. **Split long lines** with `FF 08 07 01` (page break control code) to continue on the next dialogue box
3. **Abbreviate** common terms (e.g., 아이템 → items when context is clear)
4. **Measure carefully** -- each Korean syllable block encodes to 2 bytes (0xF0-0xF5 prefix), same as Japanese kanji

A robust translation pipeline should:
1. Extract all strings with their byte lengths
2. Track translated byte lengths vs. original
3. Flag any translations that exceed the original length
4. Either auto-pad short translations or require manual adjustment for long ones
5. Rebuild each chunk with recalculated offsets

### Existing Korean Translations

Pre-translated Korean text files exist at `translated/ko/S*_STG.txt` for all 19 stages (e.g., S100_STG.txt contains 1,167 translated dialogue entries). Decoded Japanese source files are at `output/decoded/stg/S*_STG.txt`.
