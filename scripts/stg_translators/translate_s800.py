#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Translation mapping for S800_STG.txt from Japanese to Korean
# This script reads from the source file and appends translations to the output file

import os
import re

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(_SCRIPT_DIR, "..", "..")  # atl2_korean_translation/

# Character name mappings
char_map = {
    'エルク': '엘크', 'リーザ': '리자', 'シャンテ': '샨테', 'ポコ': '포코',
    'トッシュ': '토슈', 'ゴーゲン': '고겐', 'シュウ': '슈우', 'ククル': '쿠쿠루',
    'グルガ': '그루가', 'イーガ': '이가', 'サニア': '사니아', 'アーク': '아크',
    'ちょんがら': '총가라', 'ミリル': '미리르', 'リッツ': '리츠', 'セグル': '세그루'
}

# Place name mappings
place_map = {
    'ロマリア': '로말리아', 'アルディア': '알디아', 'プロディアス': '프로디아스',
    'スメリア': '스메리아', 'パレンシア': '팔렌시아', 'ニーデル': '니델',
    'ブラキア': '브라키아', 'ラムール': '라무르', 'ホルン': '호른'
}

# Open files
source_file = os.path.join(BASE_DIR, "output", "decoded", "stg", "S800_STG.txt")
output_file = os.path.join(BASE_DIR, "translated", "ko", "S800_STG.txt")

# Read how many lines have been translated already
with open(output_file, 'r', encoding='utf-8') as f:
    translated_lines = len(f.readlines())

print(f"Already translated: {translated_lines} lines")
print(f"Starting from line {translated_lines}")

# Read all source lines
with open(source_file, 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

total_lines = len(all_lines)
print(f"Total lines to translate: {total_lines}")

# Process remaining lines
remaining_lines = all_lines[translated_lines:]
print(f"Remaining lines: {len(remaining_lines)}")

# For this script, just output the status
# The actual translation will be done manually in batches
