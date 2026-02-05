#!/usr/bin/env python3
"""
Replace hiragana/katakana glyphs in COMM.IMG with Korean Hangul characters
using phonetic (by-sound) mapping.

Each kana is replaced with the Korean syllable that represents the same sound:
  あ→아, か→카, さ→사, た→타, etc.
  ア→아, カ→카, サ→사, タ→타, etc. (katakana maps to same Korean as hiragana)

The original COMM.IMG is NOT modified; a copy (COMM_IMG_KR.IMG) is created.
"""

import os
import shutil
from PIL import Image

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMM_IMG_SRC = os.path.join(SCRIPT_DIR, '..', 'COMM.IMG')
COMM_IMG_DST = os.path.join(SCRIPT_DIR, 'COMM_IMG_KR.IMG')
KOREAN_CHARS_DIR = os.path.join(SCRIPT_DIR, 'python', 'korean_chars')
MAPPING_FILE = os.path.join(SCRIPT_DIR, 'korean_charmap.txt')

# --- COMM.IMG layout constants ---
ROW_WIDTH = 896       # bytes per scanline
CHAR_W = 12           # cell width in pixels (11px glyph + 1px margin)
CHAR_H = 12           # cell height in pixels
GRID_COLS = 21        # cells per row

# --- Phonetic mapping: kana → Korean syllable ---
# Hiragana charIDs 1-80, Katakana charIDs 81-160
# Katakana has the same sounds as hiragana, so same Korean mapping.

# Hiragana (charIDs 1-80) in charID order
HIRAGANA_TO_KOREAN = {
    # Vowels (あ行)
    1: '아',   # あ (a)
    2: '이',   # い (i)
    3: '우',   # う (u)
    4: '에',   # え (e)
    5: '오',   # お (o)
    # K-row (か行)
    6: '카',   # か (ka)
    7: '키',   # き (ki)
    8: '쿠',   # く (ku)
    9: '케',   # け (ke)
    10: '코',  # こ (ko)
    # S-row (さ行)
    11: '사',  # さ (sa)
    12: '시',  # し (shi)
    13: '스',  # す (su)
    14: '세',  # せ (se)
    15: '소',  # そ (so)
    # T-row (た行)
    16: '타',  # た (ta)
    17: '치',  # ち (chi)
    18: '쓰',  # つ (tsu)
    19: '테',  # て (te)
    20: '토',  # と (to)
    # N-row (な行)
    21: '나',  # な (na)
    22: '니',  # に (ni)
    23: '누',  # ぬ (nu)
    24: '네',  # ね (ne)
    25: '노',  # の (no)
    # H-row (は行)
    26: '하',  # は (ha)
    27: '히',  # ひ (hi)
    28: '후',  # ふ (fu)
    29: '헤',  # へ (he)
    30: '호',  # ほ (ho)
    # M-row (ま行)
    31: '마',  # ま (ma)
    32: '미',  # み (mi)
    33: '무',  # む (mu)
    34: '메',  # め (me)
    35: '모',  # も (mo)
    # Y-row (や行)
    36: '야',  # や (ya)
    37: '유',  # ゆ (yu)
    38: '요',  # よ (yo)
    # R-row (ら行)
    39: '라',  # ら (ra)
    40: '리',  # り (ri)
    41: '루',  # る (ru)
    42: '레',  # れ (re)
    43: '로',  # ろ (ro)
    # W-row (わ行)
    44: '와',  # わ (wa)
    45: '오',  # を (wo, pronounced "o" in modern Japanese)
    46: '은',  # ん (n)
    # Voiced K (が行)
    47: '가',  # が (ga)
    48: '기',  # ぎ (gi)
    49: '구',  # ぐ (gu)
    50: '게',  # げ (ge)
    51: '고',  # ご (go)
    # Voiced S (ざ行)
    52: '자',  # ざ (za)
    53: '지',  # じ (ji)
    54: '즈',  # ず (zu)
    55: '제',  # ぜ (ze)
    56: '조',  # ぞ (zo)
    # Voiced T (だ行)
    57: '다',  # だ (da)
    58: '지',  # ぢ (ji, same sound as じ)
    59: '즈',  # づ (zu, same sound as ず)
    60: '데',  # で (de)
    61: '도',  # ど (do)
    # Voiced H (ば行)
    62: '바',  # ば (ba)
    63: '비',  # び (bi)
    64: '부',  # ぶ (bu)
    65: '베',  # べ (be)
    66: '보',  # ぼ (bo)
    # Semi-voiced H (ぱ行)
    67: '파',  # ぱ (pa)
    68: '피',  # ぴ (pi)
    69: '푸',  # ぷ (pu)
    70: '페',  # ぺ (pe)
    71: '포',  # ぽ (po)
    # Small kana
    72: '아',  # ぁ (small a)
    73: '이',  # ぃ (small i)
    74: '우',  # ぅ (small u)
    75: '에',  # ぇ (small e)
    76: '오',  # ぉ (small o)
    77: '야',  # ゃ (small ya)
    78: '유',  # ゅ (small yu)
    79: '요',  # ょ (small yo)
    80: '쯔',  # っ (small tsu / sokuon)
}

# Katakana (charIDs 81-160) — same sounds as hiragana
KATAKANA_TO_KOREAN = {
    # Vowels (ア行)
    81: '아',   # ア (a)
    82: '이',   # イ (i)
    83: '우',   # ウ (u)
    84: '에',   # エ (e)
    85: '오',   # オ (o)
    # K-row (カ行)
    86: '카',   # カ (ka)
    87: '키',   # キ (ki)
    88: '쿠',   # ク (ku)
    89: '케',   # ケ (ke)
    90: '코',   # コ (ko)
    # S-row (サ行)
    91: '사',   # サ (sa)
    92: '시',   # シ (shi)
    93: '스',   # ス (su)
    94: '세',   # セ (se)
    95: '소',   # ソ (so)
    # T-row (タ行)
    96: '타',   # タ (ta)
    97: '치',   # チ (chi)
    98: '쓰',   # ツ (tsu)
    99: '테',   # テ (te)
    100: '토',  # ト (to)
    # N-row (ナ行)
    101: '나',  # ナ (na)
    102: '니',  # ニ (ni)
    103: '누',  # ヌ (nu)
    104: '네',  # ネ (ne)
    105: '노',  # ノ (no)
    # H-row (ハ行)
    106: '하',  # ハ (ha)
    107: '히',  # ヒ (hi)
    108: '후',  # フ (fu)
    109: '헤',  # ヘ (he)
    110: '호',  # ホ (ho)
    # M-row (マ行)
    111: '마',  # マ (ma)
    112: '미',  # ミ (mi)
    113: '무',  # ム (mu)
    114: '메',  # メ (me)
    115: '모',  # モ (mo)
    # Y-row (ヤ行)
    116: '야',  # ヤ (ya)
    117: '유',  # ユ (yu)
    118: '요',  # ヨ (yo)
    # R-row (ラ行)
    119: '라',  # ラ (ra)
    120: '리',  # リ (ri)
    121: '루',  # ル (ru)
    122: '레',  # レ (re)
    123: '로',  # ロ (ro)
    # W-row (ワ行)
    124: '와',  # ワ (wa)
    125: '오',  # ヲ (wo, pronounced "o")
    126: '은',  # ン (n)
    # Voiced K (ガ行)
    127: '가',  # ガ (ga)
    128: '기',  # ギ (gi)
    129: '구',  # グ (gu)
    130: '게',  # ゲ (ge)
    131: '고',  # ゴ (go)
    # Voiced S (ザ行)
    132: '자',  # ザ (za)
    133: '지',  # ジ (ji)
    134: '즈',  # ズ (zu)
    135: '제',  # ゼ (ze)
    136: '조',  # ゾ (zo)
    # Voiced T (ダ行)
    137: '다',  # ダ (da)
    138: '지',  # ヂ (ji)
    139: '즈',  # ヅ (zu)
    140: '데',  # デ (de)
    141: '도',  # ド (do)
    # Voiced H (バ行)
    142: '바',  # バ (ba)
    143: '비',  # ビ (bi)
    144: '부',  # ブ (bu)
    145: '베',  # ベ (be)
    146: '보',  # ボ (bo)
    # Semi-voiced H (パ行)
    147: '파',  # パ (pa)
    148: '피',  # ピ (pi)
    149: '푸',  # プ (pu)
    150: '페',  # ペ (pe)
    151: '포',  # ポ (po)
    # Small katakana
    152: '아',  # ァ (small a)
    153: '이',  # ィ (small i)
    154: '우',  # ゥ (small u)
    155: '에',  # ェ (small e)
    156: '오',  # ォ (small o)
    157: '야',  # ャ (small ya)
    158: '유',  # ュ (small yu)
    159: '요',  # ョ (small yo)
    160: '쯔',  # ッ (small tsu / sokuon)
}

# Combine both mappings
PHONETIC_MAP = {**HIRAGANA_TO_KOREAN, **KATAKANA_TO_KOREAN}


def get_pixel(data, x, y):
    """Get 4bpp pixel value at (x, y) in the 256x256 font area of COMM.IMG."""
    byte_offset = y * ROW_WIDTH + x // 2
    byte_val = data[byte_offset]
    if x % 2 == 0:
        return byte_val & 0x0F
    else:
        return (byte_val >> 4) & 0x0F


def set_pixel(data, x, y, value):
    """Set 4bpp pixel value at (x, y) in the 256x256 font area of COMM.IMG."""
    byte_offset = y * ROW_WIDTH + x // 2
    byte_val = data[byte_offset]
    if x % 2 == 0:
        byte_val = (byte_val & 0xF0) | (value & 0x0F)
    else:
        byte_val = (byte_val & 0x0F) | ((value & 0x0F) << 4)
    data[byte_offset] = byte_val


def replace_char_glyph(data, char_id, char_img):
    """Replace a single character glyph in COMM.IMG data.

    Modifies only the target bitplane of the cell, preserving the other 3.

    Args:
        data: bytearray of the full COMM.IMG file
        char_id: 1-based character ID (1-160 for hiragana/katakana)
        char_img: 12x12 PIL Image (grayscale, 0=off, 255=on)
    """
    adjusted = char_id - 1
    cell = adjusted // 4
    bitplane = adjusted % 4
    row = cell // GRID_COLS
    col = cell % GRID_COLS

    x0 = col * CHAR_W
    y0 = row * CHAR_H
    mask = 1 << bitplane
    clear_mask = ~mask & 0x0F

    for dy in range(CHAR_H):
        for dx in range(CHAR_W):
            px = x0 + dx
            py = y0 + dy

            current = get_pixel(data, px, py)

            # Check if Korean character has a pixel at this position
            pixel_val = char_img.getpixel((dx, dy))
            if pixel_val > 0:
                current = current | mask       # Set this bitplane's bit
            else:
                current = current & clear_mask  # Clear this bitplane's bit

            set_pixel(data, px, py, current)


def generate_preview(data, output_path, scale=4):
    """Generate a preview image of the font area showing all 4 bitplanes."""
    for bit in range(4):
        mask = 1 << bit
        img = Image.new('L', (256, 256), 0)
        px = img.load()
        for y in range(256):
            for x in range(256):
                val = get_pixel(data, x, y)
                if val & mask:
                    px[x, y] = 255
        scaled = img.resize((256 * scale, 256 * scale), Image.NEAREST)
        path = output_path.replace('.png', f'_bit{bit}.png')
        scaled.save(path)
        print(f"  Preview saved: {path}")


def main():
    print("Phonetic kana → Korean replacement")
    print(f"  Mapping {len(PHONETIC_MAP)} kana charIDs to Korean syllables\n")

    # Show the mapping
    kana_names = [
        'あ','い','う','え','お','か','き','く','け','こ',
        'さ','し','す','せ','そ','た','ち','つ','て','と',
        'な','に','ぬ','ね','の','は','ひ','ふ','へ','ほ',
        'ま','み','む','め','も','や','ゆ','よ',
        'ら','り','る','れ','ろ','わ','を','ん',
        'が','ぎ','ぐ','げ','ご','ざ','じ','ず','ぜ','ぞ',
        'だ','ぢ','づ','で','ど','ば','び','ぶ','べ','ぼ',
        'ぱ','ぴ','ぷ','ぺ','ぽ','ぁ','ぃ','ぅ','ぇ','ぉ',
        'ゃ','ゅ','ょ','っ',
    ]
    print("  Hiragana mapping:")
    for i in range(0, len(kana_names), 5):
        items = []
        for j in range(i, min(i + 5, len(kana_names))):
            char_id = j + 1
            kr = PHONETIC_MAP[char_id]
            items.append(f"{kana_names[j]}→{kr}")
        print(f"    {', '.join(items)}")
    print()

    # --- Step 1: Verify Korean character PNGs ---
    print("Step 1: Verifying Korean character PNG availability...")
    unique_korean = set(PHONETIC_MAP.values())
    missing = []
    for kr_char in unique_korean:
        codepoint = ord(kr_char)
        png_path = os.path.join(KOREAN_CHARS_DIR, f'char_{codepoint:04X}.png')
        if not os.path.exists(png_path):
            missing.append(kr_char)
    if missing:
        print(f"  WARNING: {len(missing)} character PNGs missing: "
              f"{''.join(missing)}")
    else:
        print(f"  All {len(unique_korean)} unique Korean character PNGs found")

    # --- Step 2: Copy COMM.IMG ---
    print(f"\nStep 2: Copying COMM.IMG...")
    print(f"  Source: {os.path.abspath(COMM_IMG_SRC)}")
    print(f"  Destination: {os.path.abspath(COMM_IMG_DST)}")
    shutil.copy2(COMM_IMG_SRC, COMM_IMG_DST)

    with open(COMM_IMG_DST, 'rb') as f:
        data = bytearray(f.read())
    print(f"  File size: {len(data):,} bytes")

    # --- Step 3: Replace glyphs ---
    print(f"\nStep 3: Replacing 160 hiragana/katakana slots with Korean...")

    # Cache loaded Korean character images
    kr_img_cache = {}
    replaced = 0

    for char_id, kr_char in sorted(PHONETIC_MAP.items()):
        codepoint = ord(kr_char)
        png_path = os.path.join(KOREAN_CHARS_DIR, f'char_{codepoint:04X}.png')

        if not os.path.exists(png_path):
            print(f"  SKIP charID {char_id}: missing PNG for {kr_char}")
            continue

        if kr_char not in kr_img_cache:
            kr_img_cache[kr_char] = Image.open(png_path).convert('L')

        replace_char_glyph(data, char_id, kr_img_cache[kr_char])
        replaced += 1

    print(f"  Replaced {replaced}/160 character glyphs")

    # --- Step 4: Write modified file ---
    print(f"\nStep 4: Writing modified COMM.IMG...")
    with open(COMM_IMG_DST, 'wb') as f:
        f.write(data)
    print(f"  Written: {COMM_IMG_DST}")

    # --- Step 5: Generate preview images ---
    print(f"\nStep 5: Generating preview images...")
    preview_path = os.path.join(SCRIPT_DIR, 'COMM_IMG_KR_preview.png')
    generate_preview(data, preview_path)

    # --- Step 6: Save character mapping ---
    print(f"\nStep 6: Saving character mapping table...")
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        f.write("# Phonetic kana → Korean mapping for COMM_IMG_KR.IMG\n")
        f.write("# Each kana charID is replaced with the Korean syllable of the same sound\n")
        f.write("# Format: charID  kana  korean  codepoint  cell  bitplane\n\n")
        f.write("# --- Hiragana (charIDs 1-80) ---\n")
        for char_id in range(1, 81):
            kr = PHONETIC_MAP[char_id]
            kana = kana_names[char_id - 1]
            adjusted = char_id - 1
            cell = adjusted // 4
            bitplane = adjusted % 4
            f.write(f"{char_id}\t{kana}\t{kr}\tU+{ord(kr):04X}\t"
                    f"cell={cell}\tbit={bitplane}\n")
        f.write("\n# --- Katakana (charIDs 81-160) ---\n")
        kata_names = [
            'ア','イ','ウ','エ','オ','カ','キ','ク','ケ','コ',
            'サ','シ','ス','セ','ソ','タ','チ','ツ','テ','ト',
            'ナ','ニ','ヌ','ネ','ノ','ハ','ヒ','フ','ヘ','ホ',
            'マ','ミ','ム','メ','モ','ヤ','ユ','ヨ',
            'ラ','リ','ル','レ','ロ','ワ','ヲ','ン',
            'ガ','ギ','グ','ゲ','ゴ','ザ','ジ','ズ','ゼ','ゾ',
            'ダ','ヂ','ヅ','デ','ド','バ','ビ','ブ','ベ','ボ',
            'パ','ピ','プ','ペ','ポ','ァ','ィ','ゥ','ェ','ォ',
            'ャ','ュ','ョ','ッ',
        ]
        for i, char_id in enumerate(range(81, 161)):
            kr = PHONETIC_MAP[char_id]
            kana = kata_names[i]
            adjusted = char_id - 1
            cell = adjusted // 4
            bitplane = adjusted % 4
            f.write(f"{char_id}\t{kana}\t{kr}\tU+{ord(kr):04X}\t"
                    f"cell={cell}\tbit={bitplane}\n")
    print(f"  Mapping saved: {MAPPING_FILE}")

    # --- Summary ---
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Replaced: {replaced} character glyphs (phonetic mapping)")
    print(f"  Unique Korean syllables used: {len(unique_korean)}")
    print(f"  Output file: {os.path.abspath(COMM_IMG_DST)}")
    print(f"  Mapping file: {os.path.abspath(MAPPING_FILE)}")
    print(f"  Preview files: COMM_IMG_KR_preview_bit[0-3].png")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
