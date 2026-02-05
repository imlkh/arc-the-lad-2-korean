#!/usr/bin/env python3
"""
Generate bitmap font images for Korean Hangul syllables.

Renders Hangul characters (U+AC00-U+D7A3) using Korean pixel fonts.
FONT_SIZE is auto-derived from PIXEL_SIZE to ensure pixel-perfect rendering.
Output is 1-bit bitmaps compatible with the COMM.IMG 12x12 cell format
(11x11 glyph + 1px margin).
"""

import os
from PIL import Image, ImageFont, ImageDraw

# --- Configuration ---
THRESHOLD = 128  # Clean threshold for pixel font (no anti-aliasing)

# font_type = "Galmuri9"
# font_type = "GalmuriMono9"
# font_type = "Galmuri11" # good
font_type = "GalmuriMono11" # good
# font_type = "Galmuri11-bold"
# font_type = "ONE(Ed.) Galmuri11 Regular"
# font_type = "soya_godun10"
match font_type:
    case "Galmuri9":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/Galmuri9.ttf"
        PIXEL_SIZE = 9
        CHAR_SIZE = 10
    case "GalmuriMono9":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/GalmuriMono9.ttf"
        PIXEL_SIZE = 9
        CHAR_SIZE = 10
    case "Galmuri11":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/Galmuri11.ttf"
        PIXEL_SIZE = 11
        CHAR_SIZE = 12
    case "GalmuriMono11":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/GalmuriMono11.ttf"
        PIXEL_SIZE = 11
        CHAR_SIZE = 12
    case "Galmuri11-bold":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/Galmuri11-bold.ttf"
        PIXEL_SIZE = 11
        CHAR_SIZE = 12
    case "ONE(Ed.) Galmuri11 Regular":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/ONE(Ed.) Galmuri11 Regular.ttf"
        PIXEL_SIZE = 11
        CHAR_SIZE = 11
    case "soya_godun10":
        FONT_PATH = "/Users/kyounghun/Library/Fonts/soya_godun10.ttf"
        PIXEL_SIZE = 10
        CHAR_SIZE = 10

# Hangul syllable block range
HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3  # inclusive

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "output", "font", "korean_chars")
PREVIEW_PATH = os.path.join(SCRIPT_DIR, "..", "..", "output", "font", "korean_font_preview.png")


def derive_font_size(font_path, pixel_size, test_char="가", size_range=range(6, 50)):
    """Find the point size that produces the given pixel size with zero gray pixels."""
    for size in size_range:
        font = ImageFont.truetype(font_path, size)
        img = Image.new("L", (128, 128), 0)
        draw = ImageDraw.Draw(img)
        draw.text((64, 64), test_char, font=font, fill=255, anchor="mm")

        bbox = img.getbbox()
        if not bbox:
            continue
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if max(w, h) != pixel_size:
            continue
        cropped = img.crop(bbox)
        gray = sum(1 for p in cropped.getdata() if 0 < p < 255)
        if gray == 0:
            return size
    raise ValueError(
        f"No native font size found for {font_path} at {pixel_size}px "
        f"(searched {size_range.start}-{size_range.stop - 1}pt)"
    )


def find_native_size(font_path, test_char="가", size_range=range(6, 30)):
    """Detect the native pixel size of a font by finding sizes with zero gray pixels.

    At the correct native size, a pixel font renders with only 0 or 255 values
    (no anti-aliased gray pixels from interpolation).
    """
    print(f"Detecting native size for: {font_path}")
    print(f"  {'Size':>4s}  {'Glyph':>7s}  {'Gray px':>7s}  Note")
    print(f"  {'----':>4s}  {'-----':>7s}  {'------':>7s}  ----")
    for size in size_range:
        font = ImageFont.truetype(font_path, size)
        img = Image.new("L", (64, 64), 0)
        draw = ImageDraw.Draw(img)
        draw.text((32, 32), test_char, font=font, fill=255, anchor="mm")

        bbox = img.getbbox()
        if not bbox:
            continue
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        cropped = img.crop(bbox)
        gray = sum(1 for p in cropped.getdata() if 0 < p < 255)
        note = "<-- native (0 gray)" if gray == 0 else ""
        print(f"  {size:4d}  {w:3d}x{h:<3d}  {gray:7d}  {note}")
    print()


def render_char(font, char):
    """Render a character centered in an 11x11 image.

    Returns a grayscale Image with 0=off, 255=on.
    """
    # Render on an oversized canvas to capture the full glyph
    canvas_size = CHAR_SIZE * 4
    center = canvas_size // 2
    img = Image.new("L", (canvas_size, canvas_size), 0)
    draw = ImageDraw.Draw(img)
    # anchor="ms" = horizontally centered, vertically on baseline
    # All characters share a common baseline for consistent positioning
    draw.text((center, center), char, font=font, fill=255, anchor="ms")

    # Find bounding box of rendered content
    bbox = img.getbbox()
    if bbox is None:
        return Image.new("L", (CHAR_SIZE, CHAR_SIZE), 0)
    # print(bbox)

    # Crop a fixed CHAR_SIZE x CHAR_SIZE region using font metrics
    # (not per-glyph bounding box) for consistent positioning
    ascent, descent = font.getmetrics()
    total_height = ascent + descent

    # Vertical: center the ascent+descent region within CHAR_SIZE
    baseline_y = center
    text_top = baseline_y - ascent
    vert_pad = (CHAR_SIZE - total_height) // 2
    crop_top = text_top - vert_pad

    # Horizontal: centered on render point
    crop_left = center - CHAR_SIZE // 2

    out = img.crop((crop_left, crop_top, crop_left + CHAR_SIZE, crop_top + CHAR_SIZE))

    # # Crop to content
    # cropped = img.crop(bbox)
    # cw, ch = cropped.size

    # If glyph is larger than target, scale with NEAREST
    # if cw > CHAR_SIZE or ch > CHAR_SIZE:
    #     scale = min(CHAR_SIZE / cw, CHAR_SIZE / ch)
    #     new_w = max(1, int(cw * scale))
    #     new_h = max(1, int(ch * scale))
    #     cropped = cropped.resize((new_w, new_h), Image.NEAREST)
    #     cw, ch = cropped.size

    # # Center in CHAR_SIZE x CHAR_SIZE output
    # out = Image.new("L", (CHAR_SIZE, CHAR_SIZE), 0)
    # x_off = (CHAR_SIZE - cw) // 2
    # y_off = (CHAR_SIZE - ch) // 2
    # x_off = 0
    # y_off = 0
    # out.paste(cropped, (x_off, y_off))

    # Threshold to 1-bit values (stored as 0/255 in grayscale)
    out = out.point(lambda v: 255 if v >= THRESHOLD else 0)
    return out


def generate_preview(chars_and_images, cols=80, scale=4):
    """Generate a grid preview sheet of all rendered characters."""
    n = len(chars_and_images)
    rows = (n + cols - 1) // cols
    scaled = CHAR_SIZE * scale
    cell = scaled + scale  # scale-px gap between cells

    preview = Image.new("L", (cols * cell + scale, rows * cell + scale), 64)

    for idx, (codepoint, char, img) in enumerate(chars_and_images):
        r, c = divmod(idx, cols)
        x = c * cell + scale
        y = r * cell + scale
        big = img.resize((scaled, scaled), Image.NEAREST)
        preview.paste(big, (x, y))

    return preview


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    find_native_size(FONT_PATH)

    FONT_SIZE = derive_font_size(FONT_PATH, PIXEL_SIZE)
    print(f"Derived FONT_SIZE={FONT_SIZE}pt for PIXEL_SIZE={PIXEL_SIZE}px")

    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font_name = font.getname()
    print(f"Font: {font_name[0]} ({font_name[1]}), {FONT_SIZE}pt")
    print(f"Output: {CHAR_SIZE}x{CHAR_SIZE} pixels, threshold={THRESHOLD}")

    # Show sample characters
    print(f"\nSample renders:")
    for code, name in [(0xAC00, '가'), (0xD55C, '한'), (0xAE00, '글'),
                        (0xB098, '나'), (0xB9D0, '말'), (0xC548, '안'),
                        (0xB155, '녕'), (0xD558, '하'), (0xC138, '세'),
                        (0xC694, '요')]:
        img = render_char(font, chr(code))
        pixels = sum(1 for p in img.getdata() if p > 0)
        grid = ""
        for y in range(CHAR_SIZE):
            row = ""
            for x in range(CHAR_SIZE):
                row += "##" if img.getpixel((x, y)) == 255 else "  "
            grid += f"    |{row}|\n"
        print(f"  {name} (U+{code:04X}): {pixels} pixels on")
        print(grid)

    # Render all Hangul syllables
    total = HANGUL_END - HANGUL_START + 1
    print(f"Rendering {total} Hangul syllables (U+AC00-U+D7A3)...")

    chars_and_images = []
    for codepoint in range(HANGUL_START, HANGUL_END + 1):
        char = chr(codepoint)
        img = render_char(font, char)

        # Save individual PNG
        filename = f"char_{codepoint:04X}.png"
        img.save(os.path.join(OUTPUT_DIR, filename))

        chars_and_images.append((codepoint, char, img))

        # Progress
        done = codepoint - HANGUL_START + 1
        if done % 2000 == 0 or done == total:
            print(f"  {done}/{total} characters rendered")

    # Generate preview sheet
    print(f"\nGenerating preview sheet...")
    preview = generate_preview(chars_and_images, cols=100)
    preview.save(PREVIEW_PATH)
    print(f"Preview saved to: {PREVIEW_PATH}")
    print(f"  Preview size: {preview.size[0]}x{preview.size[1]} pixels")

    # Print mapping table (first 30 as sample)
    print(f"\nCharacter mapping (first 30):")
    print(f"  {'Code':>6s}  {'Hex':>6s}  Char")
    print(f"  {'----':>6s}  {'---':>6s}  ----")
    for codepoint, char, _ in chars_and_images[:30]:
        print(f"  {codepoint:6d}  {codepoint:>6X}  {char}")
    print(f"  ... ({total} total)")

    print(f"\nDone! {total} character PNGs saved to: {OUTPUT_DIR}")
    print(f"Preview sheet: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
