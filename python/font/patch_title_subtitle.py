#!/usr/bin/env python3
"""Replace the title-screen Japanese subtitle (アークザラッドII) in COMM.IMG with
Korean (아크 더 래드 II), marking the game as Korean-translated.

The title logo is a 16-bit RGB555 image wrapped in VRAM (see COMM_IMG_analysis.md).
The gold subtitle occupies bbox x70-231, y128-159 in the unwrapped 320x240 logo,
which is clear of the shared 4bpp font VRAM zone (logo pixels 0-61), so editing it
cannot corrupt the font.

Pipeline: read the bbox -> inpaint the old gold pixels (restore plate/red bg) ->
render Korean (gold vertical gradient + dark outline) -> write RGB555 back at the
wrapped VRAM offsets.
"""
import os
import struct
from PIL import Image, ImageDraw, ImageFont

ROW = 896
BBOX = (70, 128, 231, 159)  # x0, y0, x1, y1 inclusive (unwrapped logo coords)
TEXT = "아크 더 래드 II"

# A Korean-capable TrueType/OpenType font is needed to render the subtitle.
# Resolution order: $ATL2_TITLE_FONT override -> a repo-bundled font (drop one
# in python/font/fonts/ for reproducible cross-machine builds) -> common system
# fonts on macOS / Linux / Windows. If none is found the title patch is skipped
# with a warning (the Japanese subtitle is left intact) rather than crashing the
# whole rebuild.
_BUNDLED_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
# (path, face_index) pairs. face_index selects a Bold face inside a .ttc
# collection (e.g. AppleSDGothicNeo Bold = index 6); 0 for single-face files.
# A heavier "gothic" weight is preferred for the logo where available.
_FONT_CANDIDATES = [
    (os.path.join(_BUNDLED_FONT_DIR, "title.ttf"), 0),
    (os.path.join(_BUNDLED_FONT_DIR, "NanumGothicBold.ttf"), 0),
    (os.path.join(_BUNDLED_FONT_DIR, "NanumGothic.ttf"), 0),
    # macOS (Apple SD Gothic Neo Bold = face index 6)
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6),
    ("/System/Library/Fonts/Supplemental/AppleGothic.ttf", 0),
    # Linux
    ("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 0),
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0),
    ("/usr/share/fonts/truetype/noto/NotoSansKR-Bold.otf", 0),
    # Windows (Malgun Gothic Bold)
    ("C:/Windows/Fonts/malgunbd.ttf", 0),
    ("C:/Windows/Fonts/malgun.ttf", 0),
]


def _find_font():
    """Return (path, face_index) of the first available Korean font, or None.

    $ATL2_TITLE_FONT (read at call time) takes precedence over the built-in list.
    """
    env = os.environ.get("ATL2_TITLE_FONT")
    if env and os.path.isfile(env):
        return env, 0
    for path, index in _FONT_CANDIDATES:
        if path and os.path.isfile(path):
            return path, index
    return None


def _load_fitted_font(font_path, index, max_size, box_w):
    """Load the font at the largest size <= max_size whose rendered text still
    fits box_w (so a bolder/wider font auto-shrinks instead of overflowing)."""
    size = max_size
    font = ImageFont.truetype(font_path, size, index=index)
    while size > 12:
        font = ImageFont.truetype(font_path, size, index=index)
        tb = font.getbbox(TEXT, stroke_width=2)
        if (tb[2] - tb[0]) <= box_w - 2:
            break
        size -= 1
    return font, size

# Gold vertical gradient (top -> bottom) and dark outline, approximating the
# original subtitle's metallic-gold look.
GOLD_TOP = (255, 228, 120)
GOLD_BOT = (196, 132, 24)
OUTLINE = (40, 20, 0)


def _vram_off(x, y):
    """Logo pixel (x,y) -> byte offset in COMM.IMG (handles VRAM wrap)."""
    return y * ROW + 512 + x * 2 if x < 192 else (256 + y) * ROW + 512 + (x - 128) * 2


def _to555(r, g, b):
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def _from555(v):
    return ((v & 0x1F) << 3, ((v >> 5) & 0x1F) << 3, ((v >> 10) & 0x1F) << 3)


def _is_gold(r, g, b):
    return r > 140 and g > 110 and b < 110 and (r + g) > 2 * b + 80


def patch_title_subtitle(comm_img_path, out_path=None, font_size=28, dry_run=False):
    out_path = out_path or comm_img_path

    # Resolve + load the Korean font up front. If unavailable, skip the whole
    # patch (leave the original Japanese subtitle) so the rebuild never crashes.
    found = _find_font()
    if found is None:
        print("  WARNING: no Korean font found for the title subtitle "
              "(set $ATL2_TITLE_FONT or add python/font/fonts/NanumGothicBold.ttf); "
              "leaving the Japanese subtitle as-is")
        return 0
    font_path, font_index = found
    x0, y0, x1, y1 = BBOX
    try:
        font, fitted = _load_fitted_font(font_path, font_index, font_size,
                                         x1 - x0 + 1)
    except Exception as e:
        print(f"  WARNING: could not load title font {font_path}: {e}; "
              "leaving the Japanese subtitle as-is")
        return 0

    data = bytearray(open(comm_img_path, "rb").read())
    W, H = x1 - x0 + 1, y1 - y0 + 1

    # 1. Read bbox region from VRAM into an RGB image.
    region = Image.new("RGB", (W, H))
    rp = region.load()
    for yy in range(H):
        for xx in range(W):
            v = struct.unpack_from("<H", data, _vram_off(x0 + xx, y0 + yy))[0]
            rp[xx, yy] = _from555(v)

    # 2. Reconstruct the background by per-column vertical interpolation: for
    #    each column, blend from the clean row just ABOVE the box to the clean
    #    row just BELOW it. The plate is a smooth vertical gradient and the red
    #    "II" base is roughly vertical, so this removes the old katakana cleanly
    #    with no smear (unlike neighbour-averaging, which muddied red+plate).
    n_gold = sum(_is_gold(*rp[xx, yy]) for xx in range(W) for yy in range(H))

    def _vram_rgb(x, y):
        v = struct.unpack_from("<H", data, _vram_off(x, y))[0]
        return _from555(v)

    for xx in range(W):
        top = _vram_rgb(x0 + xx, y0 - 1)   # clean row above the box
        bot = _vram_rgb(x0 + xx, y1 + 1)   # clean row below the box
        for yy in range(H):
            t = (yy + 1) / (H + 1)
            rp[xx, yy] = tuple(int(top[i] + (bot[i] - top[i]) * t)
                               for i in range(3))

    # 3. Render Korean text: dark outline+base, then gold gradient interior.
    tb = font.getbbox(TEXT, stroke_width=2)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tx = (W - tw) // 2 - tb[0]
    ty = (H - th) // 2 - tb[1]

    outline_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(outline_mask).text((tx, ty), TEXT, font=font, fill=255,
                                      stroke_width=2, stroke_fill=255)
    interior_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(interior_mask).text((tx, ty), TEXT, font=font, fill=255)

    grad = Image.new("RGB", (W, H))
    gp = grad.load()
    for yy in range(H):
        t = yy / (H - 1)
        col = tuple(int(GOLD_TOP[i] + (GOLD_BOT[i] - GOLD_TOP[i]) * t)
                    for i in range(3))
        for xx in range(W):
            gp[xx, yy] = col

    region.paste(Image.new("RGB", (W, H), OUTLINE), (0, 0), outline_mask)
    region.paste(grad, (0, 0), interior_mask)

    # 4. Write RGB555 back at the wrapped offsets (bbox only -> font-safe).
    if not dry_run:
        for yy in range(H):
            for xx in range(W):
                r, g, b = rp[xx, yy]
                struct.pack_into("<H", data, _vram_off(x0 + xx, y0 + yy),
                                 _to555(r, g, b))
        with open(out_path, "wb") as f:
            f.write(data)

    print(f"  Title subtitle -> '{TEXT}': {os.path.basename(font_path)}"
          f"[{font_index}] @ {fitted}px, inpainted {n_gold} gold px, "
          f"text {tw}x{th} in {W}x{H} box")
    return n_gold


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "COMM.IMG")
    out = sys.argv[2] if len(sys.argv) > 2 else src
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 28
    patch_title_subtitle(src, out, size)
