#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation script for SG00_STG.txt from Japanese to Korean
"""

import os
import re
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(_SCRIPT_DIR, "..", "..")  # atl2_korean_translation/

# Character name mappings
NAMES = {
    'エルク': '엘크', 'リーザ': '리자', 'シャンテ': '샨테', 'ポコ': '포코',
    'トッシュ': '토슈', 'ゴーゲン': '고겐', 'シュウ': '슈우', 'ククル': '쿠쿠루',
    'グルガ': '그루가', 'イーガ': '이가', 'サニア': '사니아', 'アーク': '아크',
    'ちょんがら': '총가라', 'ミリル': '미리르', 'ロマリア': '로말리아',
    'アルディア': '알디아', 'プロディアス': '프로디아스', 'スメリア': '스메리아',
    'パレンシア': '팔렌시아', 'ガルアーノ': '갈아노', 'アンデル': '안델',
    'ヤグン': '야군', 'ゾルコン': '졸콘', 'クライム': '크라임',
    'ミルマーナ': '밀마나', 'ラマダ': '라마다', 'ロクトール': '록트르',
    'ミスロ': '미스로', 'ハンター': '헌터', 'ギルド': '길드',
    'モンスター': '몬스터', 'キャッチー・マママン': '캐치 마마만',
    'セウム': '세움', 'セグル': '세그르', 'ガルアーノ': '갈아노',
    'ネクダス': '넥다스', '笛闘大会': '격투대회', 'レジスタンス': '레지스탕스',
    'ダイナモ': '다이나모'
}

def replace_names(text):
    """Replace character names in text"""
    for jp, ko in NAMES.items():
        text = text.replace(jp, ko)
    return text

def translate_line(line):
    """Translate a single dialogue line from Japanese to Korean"""
    # Skip header, blank lines, context separators
    if not line.strip():
        return line
    if line.strip().startswith('Found'):
        return line
    if line.strip().startswith('---'):
        return line

    # Parse dialogue line: "  0xOFFSET [0xOPCODE] [script:XX XX]Japanese text"
    match = re.match(r'^(\s*0x[0-9A-F]+ \[0x[0-9A-F]+\] \[script:[^\]]+\])(.*)$', line)
    if not match:
        return line  # Return as-is if not a dialogue line

    prefix, japanese_text = match.groups()

    # Skip garbled text (contains lots of special characters or unknown chars)
    if japanese_text and (japanese_text.count('[?') > 3 or len([c for c in japanese_text if ord(c) > 12352]) < len(japanese_text) * 0.3):
        return line  # Keep garbled text as-is

    # Translate the Japanese text
    korean_text = translate_japanese_to_korean(japanese_text)

    return prefix + korean_text + '\n'

def translate_japanese_to_korean(text):
    """Core translation logic"""
    if not text:
        return text

    # Replace character names first
    text = replace_names(text)

    # Keep special tags intact [opt], [delay:XX], [item:XX], etc.
    # Translation dictionary for common phrases
    translations = {
        '選択': '선택',
        '勝利': '승리',
        '敗北': '패배',
        '賞金': '상금',
        '挑戦者': '도전자',
        '魔物': '마물',
        '出口': '출구',
        'リング': '링',
        'ゲーム': '게임',
        'メダル': '메달',
        'アイテム': '아이템',
        '交換': '교환',
        '闘技場': '투기장',
        '精霊': '정령',
        '魔調': '마력',
        '魔法': '마법',
        '聖柩': '성궤',
        '封印': '봉인',
        '世界': '세계',
        '破滅': '파멸',
        '暗黒': '암흑',
        '調': '힘',
        '希望': '희망',
        '勇者': '용자',
        '径典': '경전',
        '宝物': '보물',
        '酒場': '술집',
        '街': '마을',
        '村': '마을',
        '森': '숲',
        '木': '나무',
        '恵み': '은총',
        '加護': '가호',
        '悲しみ': '슬픔',
        '運命': '운명',
        '風のオーブ': '바람의 오브',
        '水の精霊': '물의 정령',
        '光の精霊': '빛의 정령',
        '恵みの精霊': '은총의 정령',
        '仲間': '동료',
        '敵': '적',
        '戦い': '싸움',
        '四将軍': '사장군',
        'おねえちゃん': '언니',
        'おかあさん': '엄마',
        'じいさん': '할아버지',
        '娘': '딸',
        '息子': '아들',
        '母さん': '어머니',
        '親切': '친절',
        'ケガ': '부상',
        '病気': '병',
        'ロバ': '로바',
        '報酬': '보상',
        '依頼': '의뢰',
        '危険': '위험',
        '毒ガス': '독가스',
        '地下': '지하',
    }

    for jp, ko in translations.items():
        text = text.replace(jp, ko)

    return text

def main():
    input_file = os.path.join(BASE_DIR, "output", "decoded", "stg", "SG00_STG.txt")
    output_file = os.path.join(BASE_DIR, "translated", "ko", "SG00_STG.txt")

    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")

    with open(input_file, 'r', encoding='utf-8') as fin:
        with open(output_file, 'w', encoding='utf-8') as fout:
            for line_num, line in enumerate(fin, 1):
                translated = translate_line(line)
                fout.write(translated)

                if line_num % 100 == 0:
                    print(f"Processed {line_num} lines...")

    print(f"Translation complete! Total lines: {line_num}")

if __name__ == '__main__':
    main()
