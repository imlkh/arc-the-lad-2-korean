#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(_SCRIPT_DIR, "..", "..")  # atl2_korean_translation/

# Translation dictionary for common patterns
translations = {
    # Choco's speech patterns
    "ちょこ": "초코",
    "なの": "인 거야",
    "のー": "인 거야",
    "なのー": "인 거야",
   "わーい！つかまえたー！\nこれでご飯が食べれるの": "와아! 잡았다아!\n이걸로 밥을 먹을 수 있는 거야",
    "ちょこ帰ってご飯食べるるのー": "초코 집에 돌아가서 밥 먹을 거야",
    "はやくはやくー": "빨리빨리",
    "こっちこっちー": "이쪽이야 이쪽",

    # Common expressions
    "・・・": "・・・",
    "サワサワ": "사와사와",
    "なんと！": "뭐라고!",
    "まさか": "설마",
    "ちっ！": "젠장!",
    "不覚！": "실수했군!",
    "ハンバーグ": "함박스테이크",
    "りあき": "りあき",  # Keep as is - appears to be corrupted data

    # Character names
    "エルク": "엘크",
    "リーザ": "리자",
    "シャンテ": "샨테",
    "ポコ": "포코",
    "トッシュ": "토슈",
    "ゴーゲン": "고겐",
    "シュウ": "슈우",
    "ククル": "쿠쿠루",
    "グルガ": "그루가",
    "イーガ": "이가",
    "サニア": "사니아",
    "アーク": "아크",
    "ちょんがら": "총가라",
    "ミリル": "미리르",
    "シルバ": "실바",
    "アクラ": "아크라",
    "セゼク": "세제크",
    "ラルゴ": "라르고",
    "シジリー": "시질리",
    "クエンゾ": "쿠엔조",
    "リゼッティー": "리제티",

    # Place names
    "ロマリア": "로말리아",
    "アルディア": "알디아",
    "プロディアス": "프로디아스",
    "インディゴス": "인디고스",
    "スメリア": "스메리아",
    "パレンシア": "팔렌시아",
    "ニーデル": "니델",
    "ブラキア": "브라키아",
    "ペイサス": "페이사스",
}

def translate_line(line):
    """
    Translate a single dialogue line from Japanese to Korean.
    Preserves all formatting, tags, and control codes.
    """
    # Check if this is a header, blank, or context line
    if (line.strip() == "" or
        line.startswith("Found ") or
        line.strip().startswith("---") or
        not line.strip().startswith("0x")):
        return line

    # Parse the line format: offset [opcode] [script:XX XX]Japanese text
    match = re.match(r'^(\s*0x[0-9A-F]+ \[0x[0-9A-F]+\] \[script:[0-9A-F]+ [0-9A-F]+\])(.*)$', line)
    if not match:
        return line

    prefix = match.group(1)
    japanese_text = match.group(2)

    # Translate the Japanese portion
    korean_text = japanese_text

    # Apply character name translations first
    for jp, kr in translations.items():
        korean_text = korean_text.replace(jp, kr)

    # Manual translations for specific patterns
    # (This would need to be much more comprehensive for a full translation)

    return prefix + korean_text

# File paths
input_file = os.path.join(BASE_DIR, "output", "decoded", "stg", "SI00_STG.txt.backup")
output_file = os.path.join(BASE_DIR, "translated", "ko", "SI00_STG_auto.txt")

# Read and process the file
with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

translated_lines = []
for line in lines:
    translated_lines.append(translate_line(line))

# Write the translated file
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(translated_lines)

print(f"Processed {len(lines)} lines")
