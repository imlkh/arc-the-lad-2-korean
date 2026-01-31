# COMM.IMG Font Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `COMM.IMG` |
| Size | 458,752 bytes (448 KB) |
| Layout | 896 bytes per row x 512 rows |
| Type | PS1 VRAM texture atlas |

## Structure

The file is a PS1 VRAM dump. The same bytes are interpreted differently depending on context:

| Region | Byte Range (per row) | Pixel Format | Pixel Width | Contents |
|--------|----------------------|--------------|-------------|----------|
| 4bpp area | 0-511 | 4bpp indexed | 1024 px | Fonts, sprites, UI, effects |
| 16-bit area | 512-895 | 16-bit RGB555 | 192 px | Title logo (partial) |

### Title Logo Layout (320x240, wrapped in VRAM)

The logo is **not** stored as a simple contiguous block. It wraps across VRAM rows:

| Logo Region | Source Rows | Byte Range | Pixels |
|-------------|------------|------------|--------|
| Left 192px | 0-239 | 512-895 | Direct 16-bit read |
| Right 128px | 256-495 | 640-895 | Offset: row += 256, x += 64 |

The 4bpp sprites and 16-bit logo **share overlapping VRAM bytes** (bytes 512-895). The PS1 GPU interprets the same memory differently at runtime.

## Font Glyph Layout (Left Half, Top-Left Area)

The game font is located at the **top-left corner** of the 4bpp region (starting at offset `0x000000`):

| Row | Content |
|-----|---------|
| 1 | Hiragana (あ ~ わ) |
| 2 | Katakana (ア ~ ン) |
| 3 | Latin (A-Z, a-z), numbers (0-9), symbols |
| 4-15+ | ~800+ Kanji (愛, 悪, 雨, 家, 伊, etc.) |

## UI Font (Left Half, Bottom Area)

Located in the bottom-left region:

- Large numbers (0-9) for damage/score display
- Labels: HP, MP, CHARGE, OK, DEFEAT
- Menu text: MAG, SPEED, THRCATCOUNT, JHPNXT
- Status symbols: +1 through +9, SS, hearts, diamonds, spades, clubs

## Right Half (16-bit)

- "Arc The Lad II" game title logo
- "アークザラッドII" (Japanese title)
- "(C)1996 Sony Computer Entertainment Inc."

## How to Open

### Python (recommended)

```python
import struct
from PIL import Image

data = open('COMM.IMG', 'rb').read()
row_width = 896
left_bytes = 512  # 4bpp region: 512 bytes = 1024 pixels

# --- 4bpp sprites/fonts ---
img = Image.new('RGB', (1024, 512), (0, 0, 0))
pix = img.load()
for y in range(512):
    for xb in range(left_bytes):
        offset = y * row_width + xb
        byte = data[offset]
        lo = (byte & 0x0F) * 17
        hi = ((byte >> 4) & 0x0F) * 17
        pix[xb * 2, y] = (lo, lo, lo)
        pix[xb * 2 + 1, y] = (hi, hi, hi)
img.save('COMM_4bpp.png')

# --- 16-bit logo (320x240, unwrapped from VRAM) ---
logo = Image.new('RGB', (320, 240), (0, 0, 0))
pix2 = logo.load()
x_cut = 192
for y in range(240):
    for x in range(320):
        if x < x_cut:
            offset = y * row_width + left_bytes + x * 2
        else:
            offset = (y + 256) * row_width + left_bytes + (x - x_cut + 64) * 2
        val = struct.unpack_from('<H', data, offset)[0]
        r = (val & 0x1F) << 3
        g = ((val >> 5) & 0x1F) << 3
        b = ((val >> 10) & 0x1F) << 3
        pix2[x, y] = (r, g, b)
logo.save('COMM_logo.png')
```

### TileMolester (Java)

1. Open `COMM.IMG`
2. Set codec: **4bpp linear**
3. Set width: **896 pixels**
4. Navigate to offset `0x000000`

### CrystalTile2

1. Open as raw binary
2. Set format: **4bpp**
3. Set width: **896 pixels**

## Korean Translation Notes

To translate fonts from Japanese to Korean:

1. **Extract** the glyph bitmap area from the top-left of the 4bpp region
2. **Replace** hiragana/katakana/kanji glyphs with Hangul characters, matching the same tile size
3. **Update** the character mapping table (likely in `COMM.DAT` or `SDIC.BIN`) to map text codes to new glyph positions
4. **Re-inject** the modified pixel data back into `COMM.IMG` at the same offsets

### Other files relevant to translation

| File | Role |
|------|------|
| `COMM.DAT` (66 KB) | Character mapping table / font metrics |
| `SDIC.BIN` (100 KB) | Dictionary / text decoder |
| `YEND.BIN`, `YGUILD.BIN`, `YPROP.BIN`, `YSEG.BIN`, `YSHOP.BIN` | Game text / dialogue strings |
| `S*.STG` files | Stage data with embedded text |
