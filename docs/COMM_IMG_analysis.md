# COMM.IMG Font Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `COMM.IMG` |
| Size | 458,752 bytes (448 KB) |
| Layout | 896 bytes per row x 512 rows |
| Type | PS1 VRAM texture atlas |
| VRAM position | Byte offset 640 per row (16-bit x=320, y=0) |

## Structure

The file is a PS1 VRAM texture atlas. The same bytes are interpreted differently depending on context:

| Region | Byte Range (per row) | Pixel Format | Pixel Width | Contents |
|--------|----------------------|--------------|-------------|----------|
| 4bpp area | 0-635 | 4bpp indexed | 1272 px | Fonts, sprites, UI, effects |
| 16-bit area | 636-895 | 16-bit RGB555 | 130 px | Title logo (partial strip) |
| Shared zone | 512-635 | Both formats | — | Overlap between 4bpp sprites and logo |

### Title Logo Layout (320x240, wrapped in VRAM)

The logo is **not** stored as a simple contiguous block. It wraps across VRAM rows:

| Logo Region | Source Rows | Byte Offset (per row) | Pixels |
|-------------|------------|----------------------|--------|
| Left 192px | 0-239 | 512 + x×2 | Direct 16-bit read |
| Right 128px | 256-495 | 512 + (x−128)×2 | Offset: row += 256, x += 64 |

The 4bpp sprites and 16-bit logo **share overlapping VRAM bytes** (bytes 512-635). The PS1 GPU interprets the same memory differently at runtime.

## Font Glyph Layout (Top-Left 256x256 Area)

The top-left 256×256 pixel area (128 bytes wide × 256 rows) of the 4bpp region contains the game font.

### Character Grid

| Property | Value |
|----------|-------|
| Grid size | 21 columns × 21 rows = **441 cells** |
| Cell size | 12×12 pixels (11×11 glyph + 1px right/bottom margin) |
| Used area | 21×12 = **252 pixels** per axis |
| Remaining | 4 pixels unused at right and bottom edges |
| Last cell (row 20, col 20) | **16×16 pixels** — extends into the 4px margin (icon) |

### Bitplane Encoding (4 characters per cell)

The font uses **bitplane encoding** to pack **4 separate characters** into each 11×11 cell. Each 4bpp pixel index (0-15) is treated as a 4-bit mask, where each bit represents a different character layer:

| Bit | Mask | Layer | CLUT selects |
|-----|------|-------|--------------|
| 0 | `& 1` | Character A | Indices with bit 0 set: 1,3,5,7,9,11,13,15 |
| 1 | `& 2` | Character B | Indices with bit 1 set: 2,3,6,7,10,11,14,15 |
| 2 | `& 4` | Character C | Indices with bit 2 set: 4,5,6,7,12,13,14,15 |
| 3 | `& 8` | Character D | Indices with bit 3 set: 8,9,10,11,12,13,14,15 |

Where multiple characters have a pixel at the same position, the index is the **sum of their bit masks**. For example, index 15 (all bits set) means all 4 characters have a pixel there.

At runtime, the PS1 GPU uses a **CLUT (color lookup table)** that maps only the relevant indices to a visible color, making a single character layer visible while the others appear transparent/black.

**Total characters: 441 cells × 4 bitplanes = 1,764**

### Character Layout by Bitplane

Characters are grouped in sequential sets of 4 across bitplanes within each cell. Examples:

| Cell | Bit 0 (`&1`) | Bit 1 (`&2`) | Bit 2 (`&4`) | Bit 3 (`&8`) |
|------|-------------|-------------|-------------|-------------|
| 0 | あ | い | う | え |
| 1 | お | か | き | く |
| 2 | け | こ | さ | し |
| 3 | す | せ | そ | た |
| 21 | ア | カ | キ | ク |
| 42 | I | J | K | L |
| 48 | g | h | i | j |
| 66 | → | ← | ↑ | ↓ |

### Content by Row (approximate)

| Grid Row | Cells | Content |
|----------|-------|---------|
| 0 | 0-20 | Hiragana (あ~ん), punctuation |
| 1 | 21-41 | Katakana (ア~ン), symbols |
| 2 | 42-62 | Latin (A-Z, a-z), numbers (0-9) |
| 3 | 63-83 | Symbols, arrows, first kanji |
| 4-19 | 84-419 | Kanji |
| 20 | 420-440 | Kanji (continued), UI elements (+1~+9, SS), cursor icon |

### How to Extract Characters

```python
from PIL import Image

data = open('COMM.IMG', 'rb').read()
row_width = 896
char_w, char_h = 12, 12  # 12x12 cell (11x11 glyph + 1px margin)
grid_cols, grid_rows = 21, 21

# Build 256x256 index map
indices = [[0]*256 for _ in range(256)]
for y in range(256):
    for xb in range(128):
        offset = y * row_width + xb
        byte = data[offset]
        indices[y][xb * 2] = byte & 0x0F
        indices[y][xb * 2 + 1] = (byte >> 4) & 0x0F

# Extract 4 bitplane layers
for bit in range(4):
    mask = 1 << bit
    for cell in range(441):
        grow, gcol = cell // grid_cols, cell % grid_cols
        x0 = gcol * char_w
        y0 = grow * char_h

        # Last cell is 16x16 (extends into margin)
        if grow == 20 and gcol == 20:
            w, h = 16, 16
        else:
            w, h = char_w, char_h

        img = Image.new('L', (w, h), 0)
        px = img.load()
        for dy in range(h):
            for dx in range(w):
                if indices[y0 + dy][x0 + dx] & mask:
                    px[dx, dy] = 255
        # Character index: cell * 4 + bit
        img.save(f'char_{cell:03d}_bit{bit}.png')
```

## VRAM Mapping

The font area is **static** — byte-for-byte identical between `COMM.IMG` and the PS1 VRAM at runtime (confirmed by comparing with a VRAM dump). The font is loaded once and never changes.

| Property | Value |
|----------|-------|
| PS1 VRAM total | 1 MB, organized as 1024×512 halfword grid (2048 bytes/row) |
| COMM.IMG position | Byte 640 per row (16-bit x=320, y=0) |
| Font area in VRAM | x=320, y=0, 256×256 4bpp texels |
| Texture page | 4bpp page = 256×256 texels = 32 KB; X aligned to 64-halfword multiples, Y to 256-line multiples |
| Upload mechanism | CPU-to-VRAM via GPU command GP0(A0h), or DMA channel 2 |

The font area occupies one 4bpp texture page starting at VRAM x=320 (halfword column 320 = 5th 64-halfword block). Per PSX SPX, 4bpp texture pages must be X-aligned to multiples of 64 halfwords (128 bytes) and Y-aligned to multiples of 256 lines. The font at (320, 0) satisfies both constraints.

### CLUTs Found in VRAM

Per PSX SPX, 4bpp CLUTs are 16×1 images (16 colors × 16-bit RGB555 = 32 bytes). CLUT X positions must be multiples of 16 halfwords in VRAM. CLUT Y can be any row 0-511.

| CLUT | VRAM Position | Description |
|------|---------------|-------------|
| Grayscale | (144, 501) | Smooth 16-step gradient, 0-248 |
| Dialogue | (368, 242) | Indices 0-11 = black (shadow invisible), 12 = cyan, 13-14 = white, 15 = orange/gold |

Both CLUT X positions (144, 368) are multiples of 16, consistent with the hardware requirement.

The dialogue CLUT demonstrates the bitplane selection: by mapping most indices to black and only specific ones to visible colors, the game selects which character layer to display. Per PSX SPX, color value 0x0000 is rendered as fully transparent in textured primitives, so the black indices effectively become invisible.

## UI Font (Left Half, Bottom Area)

Located in the bottom-left region (below the 256x256 font area):

- Large numbers (0-9) for damage/score display
- Labels: HP, MP, CHARGE, OK, DEFEAT
- Menu text: MAG, SPEED, THRCATCOUNT, JHPNXT
- Status symbols: hearts, diamonds, spades, clubs

## Right Half (16-bit)

- "Arc The Lad II" game title logo
- "アークザラッドII" (Japanese title)
- "(C)1996 Sony Computer Entertainment Inc."

## Korean Translation Notes

To translate fonts from Japanese to Korean:

1. **Extract** all 1,764 characters from the 4 bitplanes
2. **Replace** hiragana/katakana/kanji glyphs with Hangul characters, re-encoding as bitplanes (4 characters packed per cell)
3. **Update** the character mapping table (likely in `COMM.DAT` or `SDIC.BIN`) to map text codes to new glyph positions
4. **Re-inject** the modified pixel data back into `COMM.IMG` at the same offsets

### Key constraint

Each group of 4 characters shares the same 12×12 cell (11×11 glyph area + 1px margin). Where two or more characters in the same group have a pixel at the same position, the indices combine via bitwise OR. This means characters within the same cell group can overlap — the PS1 CLUT ensures only one is visible at a time.

### Other files relevant to translation

| File | Role |
|------|------|
| `COMM.DAT` (66 KB) | Character mapping table / font metrics |
| `SDIC.BIN` (100 KB) | Dictionary / text decoder |
| `YEND.BIN`, `YGUILD.BIN`, `YPROP.BIN`, `YSEG.BIN`, `YSHOP.BIN` | PS1 MIPS executable overlays (credits, guild, items, characters, shop) |
| `S*.STG` files | Stage data with embedded text |

### Character index tables in RAM

Found in a RAM dump at runtime:

| Address | Entries | Description |
|---------|---------|-------------|
| `0x80183344` | 381 | Values 0-379, 214 unique — likely text-to-glyph mapping |
| `0x801F0400` | 1,102 | Values 0-1023, 690+ unique — larger character table |
