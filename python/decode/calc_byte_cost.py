#!/usr/bin/env python3
"""Calculate byte cost of Korean translations with FF control codes.

Uses the actual unified_charmap.txt and the same encoding rules as patch_korean.py:
- charID 1-238 (0x01-0xEE): 1 byte
- charID 239+: 2 bytes (F0+ prefix)
- [FF:XX YY ZZ] = 1 + len(params) bytes
- [opt] = 1 byte (0xEF)
- Spaces = 0 bytes (removed by encoder)
- Newlines/\n = 4 bytes (FF 05 01 01)
- Punctuation uses charID-based encoding (same 1 or 2 byte rules)
"""
import os
import sys


def load_charmap():
    """Load unified charmap and return korean_char -> charID mapping."""
    charmap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'output', 'patched', 'unified_charmap.txt')
    mapping = {}
    with open(charmap_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                char = parts[0]
                char_id = int(parts[1])
                mapping[char] = char_id
    return mapping


def char_id_to_byte_count(char_id):
    """Return byte count for a given charID."""
    if 1 <= char_id <= 0xEE:  # 1-238
        return 1
    elif char_id >= 239:
        return 2
    return 0


# Punctuation map from patch_korean.py (char -> charID)
PUNCT_MAP = {
    "、": 0xE4, "。": 0xEC, "！": 0xED, "？": 0xEE,
    "…": 0xE5, "・": 250, "ー": 0xE3, "～": 0xEA,
    "(": 245, ")": 246, "「": 251, "」": 252,
    ",": 247, ".": 248, ":": 249,
    "?": 0xEE, "!": 0xED, "~": 0xEA,
    "-": 0xE7, "/": 232, "／": 232, '"': 235,
    " ": None,
}


def calc_cost(text, charmap):
    """Calculate byte cost of a Korean text string with FF tags.

    Mirrors the logic in encode_korean_text() from patch_korean.py.
    """
    # Normalize ellipsis like the encoder does
    text = text.replace('...', '\u2026')  # ... -> …
    text = text.replace('..', '\u2026')   # .. -> …

    cost = 0
    i = 0
    unknown_chars = []

    while i < len(text):
        ch = text[i]

        # Newline -> FF 05 01 01 = 4 bytes
        if ch == "\n":
            cost += 4
            i += 1
            continue

        # Literal \n
        if ch == "\\" and i + 1 < len(text) and text[i + 1] == "n":
            cost += 4
            i += 2
            continue

        # Control code tags
        if ch == "[":
            end = text.find("]", i)
            if end != -1:
                tag = text[i+1:end]

                if tag.startswith("delay:"):
                    cost += 4  # FF 03 XX 01
                elif tag == "box:system":
                    cost += 4
                elif tag == "box:close":
                    cost += 4
                elif tag == "box:speech":
                    cost += 4
                    # Note: at string start, encoder adds 0xA0 space byte
                    # but that's for the [box:speech] display bug fix
                elif tag == "box:narration":
                    cost += 4
                elif tag == "cursor":
                    cost += 4
                elif tag == "br":
                    cost += 4
                elif tag == "opt":
                    cost += 1  # EF
                elif tag.startswith("FF:"):
                    parts = tag[3:].split()
                    cost += 1 + len(parts)  # FF + params
                elif tag.startswith("num:"):
                    cost += 4
                elif tag.startswith("item:"):
                    cost += 4
                elif tag.startswith("name:"):
                    cost += 4
                # else: unknown tag, 0 bytes

                i = end + 1
                continue

        # Korean character from charmap
        if ch in charmap:
            char_id = charmap[ch]
            cost += char_id_to_byte_count(char_id)
            i += 1
            continue

        # Punctuation
        if ch in PUNCT_MAP:
            char_id = PUNCT_MAP[ch]
            if char_id is not None:
                cost += char_id_to_byte_count(char_id)
            # Space (None) = 0 bytes
            i += 1
            continue

        # Unknown character
        unknown_chars.append(ch)
        i += 1

    return cost, unknown_chars


def find_2byte_chars(text, charmap):
    """Return list of chars in text that encode as 2 bytes."""
    two_byte = []
    for ch in text:
        if ch in charmap:
            char_id = charmap[ch]
            if char_id >= 239:
                two_byte.append((ch, char_id))
        elif ch in PUNCT_MAP:
            char_id = PUNCT_MAP[ch]
            if char_id is not None and char_id >= 239:
                two_byte.append((ch, char_id))
    return two_byte


def main():
    charmap = load_charmap()

    # Test entries from command line
    if len(sys.argv) > 2:
        budget = int(sys.argv[1])
        text = sys.argv[2]
        cost, unknowns = calc_cost(text, charmap)
        status = "OK" if cost <= budget else f"OVER by {cost - budget}"
        print(f"Budget: {budget}, Cost: {cost} -> {status}")
        print(f"  Text: {text}")
        if unknowns:
            print(f"  Unknown chars: {unknowns}")
        two_byte = find_2byte_chars(text, charmap)
        if two_byte:
            print(f"  2-byte chars: {', '.join(f'{c}(id={cid})' for c, cid in two_byte)}")
        return

    # Batch test
    tests = [
        # (budget, text, description)
        (31, "소드[FF:1A 00 00]블레이드[FF:1A 00 00]에지[FF:1A 00 00]검", "767: swords"),
        (41, "슬레이어[FF:1A 00 00]웨폰[FF:1A 00 00]카타나[FF:1A 00 00]사무라이블레이드", "768: special swords"),
        (17, "핸드액스[FF:1A 00 00]해머", "769: axe+hammer"),
        (32, "라이트해머[FF:1A 00 00]액스[FF:1A 00 00]워해머", "770: hammers"),
        (27, "라이트플레일[FF:1A 00 00]플레일[FF:1A 00 00]플레일", "771: flails"),
        (25, "체인플레일[FF:1A 00 00]모닝스타", "772: flails2"),
        (22, "나이프[FF:1A 00 00]크리스[FF:1A 00 00]나이프", "773: knives"),
        (39, "대거[FF:1A 00 00]실버나이프[FF:1A 00 00]쇼트소드[FF:1A 00 00]카타르", "774: daggers"),
        (25, "스피어[FF:1A 00 00]스피어[FF:1A 00 00]트라이덴트", "775: spears"),
        (42, "파르티잔[FF:1A 00 00]할버드[FF:1A 00 00]스피어[FF:1A 00 00]클럽[FF:1A 00 00]폴", "776: polearms"),
        (34, "파워클럽[FF:1A 00 00]메탈스트라이커[FF:1A 00 00]보팔클럽", "777: clubs"),
        (14, "완드[FF:1A 00 00]로드", "778: wands"),
        (32, "스태프[FF:1A 00 00]스케일로드[FF:1A 00 00]워스태프", "779: staves"),
        (49, "아이언너클[FF:1A 00 00]클로[FF:1A 00 00]너클[FF:1A 00 00]클로[FF:1A 00 00]피스트", "780: fists"),
        (54, "라이트슈즈[FF:1A 00 00]무릎보호대[FF:1A 00 00]슈즈[FF:1A 00 00]니들슈즈[FF:1A 00 00]드래곤부츠", "781: shoes"),
        (59, "라이트심벌[FF:1A 00 00]사운드[FF:1A 00 00]크래시심벌[FF:1A 00 00]심벌[FF:1A 00 00]위프[FF:1A 00 00]니들", "782: cymbals"),
        (13, "드래곤위프", "783: whip"),
        (46, "머신건[FF:1A 00 00]니들건[FF:1A 00 00]바렛[FF:1A 00 00]디멘션건", "784: guns"),
        (65, "패드[FF:1A 00 00]비트어태커[FF:1A 00 00]파워패드[FF:1A 00 00]브레이커[FF:1A 00 00]팽[FF:1A 00 00]비크[FF:1A 00 00]팽", "785: pads/fangs"),
        (22, "팽[FF:1A 00 00]다이노팽", "786: fangs"),
        (6, "마스크", "787: mask"),
        (81, "메탈페이스[FF:1A 00 00]셰도우룩[FF:1A 00 00]퍼플아이[FF:1A 00 00]라이트시클[FF:1A 00 00]사이즈[FF:1A 00 00]시클[FF:1A 00 00]보팔사이즈[FF:1A 00 00]블러디문", "788: sickles"),
        (16, "블랙카드[FF:1A 00 00]카드", "789: cards"),
        (12, "미라클카드", "790: cards2"),
        (33, "화이트비즈[FF:1A 00 00]로자리[FF:1A 00 00]데들리프레이", "791: beads"),
        (34, "샷건[FF:1A 00 00]돌리샷[FF:1A 00 00]그레네이드", "792: guns2"),
    ]

    print("=== Byte Cost Calculator ===")
    print(f"Charmap loaded: {len(charmap)} characters\n")

    over_count = 0
    total_entries = len(tests)
    for budget, text, desc in tests:
        cost, unknowns = calc_cost(text, charmap)
        remaining = budget - cost
        if cost > budget:
            status = f"OVER +{cost - budget}"
            over_count += 1
        else:
            status = f"OK (-{remaining})"

        print(f"  [{budget:3d}] cost={cost:3d} {status:12s} | {desc}")

        if cost > budget:
            print(f"         Text: {text}")
            two_byte = find_2byte_chars(text, charmap)
            if two_byte:
                print(f"         2-byte chars: {', '.join(f'{c}(id={cid})' for c, cid in two_byte)}")

        if unknowns:
            print(f"         Unknown chars: {set(unknowns)}")

    print(f"\n  Total: {total_entries} entries, {over_count} over budget")
    if over_count == 0:
        print("  All entries fit within budget!")


if __name__ == '__main__':
    main()
