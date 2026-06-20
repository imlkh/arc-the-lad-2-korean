#!/usr/bin/env python3
"""Fix 78 truncated entries in SCPS_100_26.txt by applying shortened translations.

Each replacement has been manually crafted to fit within the original Japanese byte
count while preserving meaning. The script validates every replacement against the
byte limit before applying.

Usage:
    python python/tools/fix_truncated_scps.py           # Apply fixes
    python python/tools/fix_truncated_scps.py --dry-run  # Validate only, no changes
"""

import os
import sys
import argparse
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)  # python/
PATCH_DIR = os.path.join(PYTHON_DIR, "patch")
sys.path.insert(0, PATCH_DIR)

from patch_korean import (
    load_decode_table, encode_korean_text, parse_bin_translation_file,
    build_encode_table, char_id_to_bytes, BASE_DIR, OUTPUT_DIR,
)

TRANSLATED_DIR = os.path.join(BASE_DIR, "translated", "ko")
SCPS_FILE = os.path.join(TRANSLATED_DIR, "SCPS_100_26.txt")


def load_unified_charmap():
    """Load the unified Korean character mapping from unified_charmap.txt."""
    charmap_path = os.path.join(OUTPUT_DIR, "unified_charmap.txt")
    if not os.path.exists(charmap_path):
        print(f"ERROR: unified_charmap.txt not found at {charmap_path}")
        print("       Run patch_all.py first to create the unified character mapping.")
        sys.exit(1)

    korean_mapping = {}
    with open(charmap_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    korean_mapping[parts[0]] = int(parts[1])
                except (ValueError, IndexError):
                    continue
    return korean_mapping


# All 78 replacements: offset_hex -> (old_text, new_text)
REPLACEMENTS = {
    # --- Overflow 7B (1) ---
    "0x000D387A": ("각성하지 않으면 사용할수없습니다", "각성 안하면 사용불가"),

    # --- Overflow 5B (3) ---
    "0x000D43C8": ("체인지할 수 있는 레벨에 도달하지 않았습니다", "체인지 레벨에 미달입니다"),
    "0x000D4460": ("얼마나 올립니까?[opt]좌우키로 자릿수,[opt]상하키로 숫자가[opt]바뀝니다",
                   "얼마나 올릴까?[opt]좌우키 자릿수[opt]상하키 숫자[opt]바뀝니다"),

    # --- Overflow 4B (4) ---
    "0x000D359A": ("데이터가 손상되었습니다", "데이터가 손상됐다"),
    "0x000D4006": ("무엇을 하시겠습니까?", "어떻게 할까요?"),
    "0x000D5C26": ("얼어붙는 숨결이 적의 움직임을 둔하게 한다", "얼어붙는 숨결이 적을 둔하게 한다"),
    "0x000D687E": ("장비할 수 있는 캐릭터가 없는 것 같습니다", "장비할 수 있는 캐릭터 없습니다"),

    # --- Overflow 3B (8) ---
    "0x000D37CA": ("아이템이 가득차서 해제할수없습니다", "아이템이 가득차서 해제불가"),
    "0x000D3820": ("몬스터가 가득찼습니다만 포기합니까?", "몬스터 가득찼습니다 포기할까?"),
    "0x000D38C2": ("배틀중인 캐릭터는 헤어질수없습니다", "배틀중 캐릭터는 헤어질수없다"),
    "0x000D4168": ("소지품이 가득입니다. 무언가 파시겠습니까?", "소지품이 가득입니다. 뭔가 팔까요?"),
    "0x000D4484": ("괜찮습니까?", "괜찮나?"),
    "0x000D590A": ("술중에 빠진 자의 목숨을 빼앗는다", "술에 빠진 자 목숨을 빼앗는다"),
    "0x000D5F1E": ("바람의 은총이 폭풍에서 몸을 보호한다", "바람의 은총이 폭풍에서 보호한다"),
    "0x000D64DE": ("소용돌이치는 불꽃이 덮쳐온다", "소용돌이 불꽃이 덮친다"),

    # --- Overflow 2B (19) ---
    "0x000D346A": ("얼굴던지기", "머리던지기"),
    "0x000D3534": ("L2버튼에 등록되었습니다", "L2버튼에 등록됐습니다"),
    "0x000D3544": ("R2버튼에 등록되었습니다", "R2버튼에 등록됐습니다"),
    "0x000D3574": ("저장되지 않았습니다", "저장 안됐습니다"),
    "0x000D35C2": ("데이터를 선택해주세요", "데이터 선택해주세요"),
    "0x000D380A": ("아이템이 가득찼습니다만 포기합니까?", "아이템이 가득찼습니다 포기할까?"),
    "0x000D403E": ("여기서 장비하고 가시겠습니까?", "여기서 장비하시겠습니까?"),
    "0x000D57E6": ("얼어붙는 맹렬한 눈보라가 덮쳐온다", "얼어붙는 맹렬한 눈보라가 덮친다"),
    "0x000D5864": ("풍신・뇌신 사이에 있는 적을 바람과 번개가 덮친다",
                   "풍신・뇌신 사이의 적을 바람과 번개가 덮친다"),
    "0x000D5984": ("마비 성분을 품은 바람이 덮쳐온다", "마비 성분 품은 바람이 덮쳐온다"),
    "0x000D59F8": ("적을 휘말리면서 자신의 목숨을 끊는다", "적을 휘말리며 자신 목숨을 끊는다"),
    "0x000D5C62": ("성스러운 숨결로 악당을 장사지낸다", "성스러운 숨결로 악당 장사지낸다"),
    "0x000D5E50": ("딱딱한 바닥을 적에게 맞혀 큰 데미지", "딱딱한 바닥을 적에게 맞혀 데미지"),
    "0x000D610E": ("적의 졸음을 유도하여 싸울 의지를 빼앗는다", "적의 졸음을 유도해 싸울 의지를 빼앗는다"),
    "0x000D679C": ("이 합성되었습니다", "이 합성됐습니다"),
    "0x000D67C8": ("골드 필요합니다.", "골드 필요합니다"),
    "0x000D6894": ("이 아이템은 가지고 있지 않습니다", "이 아이템은 가지고 있지 않다"),
    "0x000D68C6": ("이미 선택되어 있습니다", "이미 선택됐습니다"),
    "0x000D6A46": ("돌아오지 않는 숲", "불귀의 숲"),
    "0x000D6B1C": ("돌아오지 않는 숲", "불귀의 숲"),
    "0x000D6B3E": ("돌아오지 않는 숲", "불귀의 숲"),

    # --- Overflow 1B (43) ---
    "0x000D2BBC": ("히포그리폰", "히포그리프"),
    "0x000D2DA2": ("마을사람", "마을주민"),
    "0x000D2EAC": ("헤롱헤롱랩퍼", "헤롱헤롱래퍼"),
    "0x000D303A": ("대단한바닥만들기", "거대한바닥만들기"),
    "0x000D3284": ("메키메키", "메기메기"),
    "0x000D329E": ("키라키라", "기라기라"),
    "0x000D32A4": ("포코포코", "보코보코"),
    "0x000D331E": ("버리지않기", "안버리기"),
    "0x000D3340": ("헤어지지않기", "안헤어지기"),
    "0x000D3442": ("지팡이", "스태프"),
    "0x000D3454": ("채찍", "회초리"),
    "0x000D3494": ("어깨보호대", "어깨가드"),
    "0x000D369C": ("데이터를 저장중입니다", "데이터 저장중입니다"),
    "0x000D36AA": ("데이터를 불러오는중", "데이터 불러오는중"),
    "0x000D36F2": ("이 아이템은 사용할수없습니다", "이 아이템 사용할수없습니다"),
    "0x000D3726": ("이름을 변경했습니다", "이름 변경했습니다"),
    "0x000D3734": ("이름을 원래대로 돌렸습니다", "이름 원래대로 돌렸습니다"),
    "0x000D3744": ("모든 캐릭터가 장비할수없는 아이템입니다", "모든 캐릭터 장비할수없는 아이템입니다"),
    "0x000D3868": ("전투불능 캐릭터가 없습니다", "전투불능 캐릭터 없습니다"),
    "0x000D3F9C": ("던지기 레벨이 3이 된다", "던지기 레벨 3이 된다"),
    "0x000D3FA8": ("던지기 레벨이 0이 된다", "던지기 레벨 0이 된다"),
    "0x000D448C": ("다른 사람에게도[opt]줄까요?", "다른 사람에게[opt]줄까요?"),
    "0x000D4D42": ("쿠쿠루", "구쿠루"),
    "0x000D4E40": ("불꽃의", "화염의"),
    "0x000D4E78": ("바람의", "풍의"),
    "0x000D54D2": ("특정적으로부터 데미지감소", "특정적에게서 데미지감소"),
    "0x000D58A8": ("지상에 남겨진 영혼을 성불시킨다", "지상에 남겨진 영혼 성불시킨다"),
    "0x000D58D8": ("정령의 힘이 빛과 함께 적을 장사지낸다", "정령의 힘이 빛과 함께 적 장사지낸다"),
    "0x000D5956": ("맹독을 품은 바람이 덮쳐온다", "맹독 품은 바람이 덮쳐온다"),
    "0x000D5CC4": ("이 숨결을 맞으면 맹렬한 졸음에 빠진다", "이 숨결 맞으면 맹렬한 졸음에 빠진다"),
    "0x000D5CDE": ("적의 급소를 찔러 움직임을 멈춘다", "적의 급소를 찔러 움직임 멈춘다"),
    "0x000D5EF6": ("물의 은총이 눈보라에서 몸을 보호한다", "물의 은총이 눈보라에서 몸 보호한다"),
    "0x000D5F0A": ("불꽃의 은총이 고열에서 몸을 보호한다", "불꽃의 은총이 고열에서 몸 보호한다"),
    "0x000D664E": ("이 되었다", "이 됐다"),
    "0x000D667A": ("을 배웠다", "배웠다"),
    "0x000D66B4": ("을 손에 넣었다", "손에 넣었다"),
    "0x000D6774": ("의 전용으로 했습니다", "전용으로 했습니다"),
    "0x000D68D2": ("합성되는 아이템을 변경했습니다", "합성되는 아이템 변경했습니다"),
    "0x000D6A96": ("유드의 마을", "유드 마을"),
    "0x000D72C8": ("살류족의 마을터", "살류족 마을터"),
    "0x000D7956": ("확대축소", "확/축"),
    "0x000D799A": ("동료에서빼기", "동료에서제거"),
}


def validate_replacements(korean_mapping, decode_table):
    """Validate all replacements encode within the original byte limit.

    Returns (passed, failed) lists of (offset, old, new, encoded_len, orig_len).
    """
    encode_table = build_encode_table(decode_table)
    passed = []
    failed = []

    # Parse the translation file to get orig_length for each offset
    entries = parse_bin_translation_file(SCPS_FILE)
    orig_lengths = {}
    for entry in entries:
        offset_hex = f"0x{entry['offset']:08X}"
        orig_lengths[offset_hex] = entry["orig_length"]

    for offset_hex, (old_text, new_text) in sorted(REPLACEMENTS.items()):
        orig_len = orig_lengths.get(offset_hex)
        if orig_len is None:
            failed.append((offset_hex, old_text, new_text, -1, -1, "offset not found"))
            continue

        encoded = encode_korean_text(new_text, korean_mapping, decode_table)
        encoded_len = len(encoded)

        if encoded_len <= orig_len:
            passed.append((offset_hex, old_text, new_text, encoded_len, orig_len))
        else:
            overflow = encoded_len - orig_len
            failed.append((offset_hex, old_text, new_text, encoded_len, orig_len,
                           f"still overflows by {overflow}B"))

    return passed, failed


def apply_replacements(dry_run=False):
    """Apply all replacements to SCPS_100_26.txt."""
    # Load charmap and decode table
    korean_mapping = load_unified_charmap()
    decode_table = load_decode_table()

    print(f"Loaded {len(korean_mapping)} Korean character mappings")
    print(f"Processing {len(REPLACEMENTS)} replacements...\n")

    # Validate
    passed, failed = validate_replacements(korean_mapping, decode_table)

    # Report validation
    print(f"=== Validation Results ===")
    print(f"  PASS: {len(passed)}/{len(REPLACEMENTS)}")
    print(f"  FAIL: {len(failed)}/{len(REPLACEMENTS)}")
    print()

    if failed:
        print("=== FAILED entries ===")
        for item in failed:
            offset_hex, old_text, new_text = item[0], item[1], item[2]
            reason = item[5] if len(item) > 5 else f"encoded={item[3]}, limit={item[4]}"
            print(f"  {offset_hex}: {reason}")
            print(f"    OLD: {old_text}")
            print(f"    NEW: {new_text}")
        print()

    if dry_run:
        print("[DRY RUN] No changes applied.")
        if passed:
            print(f"\n=== Would apply {len(passed)} replacements ===")
            for offset_hex, old_text, new_text, enc_len, orig_len in passed:
                slack = orig_len - enc_len
                print(f"  {offset_hex} [{enc_len}/{orig_len}B, slack={slack}]: "
                      f"{old_text} → {new_text}")
        return len(failed) == 0

    if failed:
        print("Fix failed entries before applying. Aborting.")
        return False

    # Read the file
    with open(SCPS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Apply each replacement
    applied = 0
    not_found = []
    for offset_hex, (old_text, new_text) in sorted(REPLACEMENTS.items()):
        # Match the line pattern: "  0xOFFSET [  LEN] old_text"
        # We need to replace only the text portion after the bracket
        pattern = re.compile(
            r"^(  " + re.escape(offset_hex) + r" \[\s*\d+\] )" + re.escape(old_text) + r"$",
            re.MULTILINE
        )
        new_content = pattern.sub(r"\g<1>" + new_text.replace("\\", "\\\\"), content, count=1)
        if new_content == content:
            not_found.append((offset_hex, old_text))
        else:
            content = new_content
            applied += 1

    # Write back
    with open(SCPS_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"=== Applied {applied}/{len(REPLACEMENTS)} replacements ===")
    if not_found:
        print(f"\n=== {len(not_found)} entries NOT FOUND in file ===")
        for offset_hex, old_text in not_found:
            print(f"  {offset_hex}: {old_text}")

    return len(not_found) == 0 and len(failed) == 0


def main():
    parser = argparse.ArgumentParser(description="Fix truncated SCPS_100_26.txt entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only, don't modify the file")
    args = parser.parse_args()

    success = apply_replacements(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
