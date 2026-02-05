#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch translator for S800_STG.txt from Japanese to Korean
Processes the full file with translation rules
"""

import re

# Character/Place name mappings
CHAR_MAP = {
    'エルク': '엘크', 'リーザ': '리자', 'シャンテ': '샨테', 'ポコ': '포코',
    'トッシュ': '토슈', 'ゴーゲン': '고겐', 'シュウ': '슈우', 'ククル': '쿠쿠루',
    'グルガ': '그루가', 'イーガ': '이가', 'サニア': '사니아', 'アーク': '아크',
    'ちょんがら': '총가라', 'ミリル': '미리르', 'リッツ': '리츠', 'セグル': '세그루',
    'ロマリア': '로말리아', 'アルディア': '알디아', 'プロディアス': '프로디아스',
    'スメリア': '스메리아', 'パレンシア': '팔렌시아', 'ニーデル': '니델',
    'ブラキア': '브라키아', 'ラムール': '라무르', 'ホルン': '호른',
    'ガルアーノ': '갈아노', 'アンデル': '안델', 'ヤグン': '야군',
    'ゾルコン': '졸콘', 'クライム': '크라임'
}

# Common translation patterns
PATTERNS = {
    # Greetings & common phrases
    'いらっしゃいませ': '어서 오세요',
    'ありがとう': '고마워',
    'ごめんなさい': '미안해요',
    'すみません': '죄송합니다',
    'お願いします': '부탁드려요',

    # Question patterns
    'どうしたの': '어떻게 된 거야',
    'なぜ': '왜',
    'どこ': '어디',
    'いつ': '언제',
    'だれ': '누구',

    # Witch-related terms
    '魔女': '마녀',
    '寺院': '사원',
    '街': '거리',
    '村': '마을',
    '岩': '바위',
    '川': '강',
    '花': '꽃',
    '占い': '점쟁이',
    '新聞': '신문',
    '酒場': '술집',
    'ギルド': '길드',
    'モンスター': '몬스터',
    '教皇': '교황',
    '警察': '경찰',

    # Emotional/Situational
    '怖い': '무서워',
    '恐い': '무서워',
    '嬉しい': '기쁘다',
    '悲しい': '슬프다',
    '困る': '곤란하다',
    '心配': '걱정',
    '安心': '안심',
    '危険': '위험',
    '災い': '재앙',
    '悪魔': '악마',
    '呪い': '저주',
    '滅ぼす': '멸망시키다',
    '焼く': '태우다',
    '壊れる': '망가지다',

    # Actions
    '捕まる': '잡히다',
    '逃げる': '도망치다',
    '帰る': '돌아가다',
    '行く': '가다',
    '来る': '오다',
    '見る': '보다',
    '聞く': '듣다',
    '食べる': '먹다',
    '飲む': '마시다',
    '遊ぶ': '놀다',
    '忘れる': '잊다',
    '思い出す': '기억하다',

    # Time
    '昨日': '어제',
    '今日': '오늘',
    '明日': '내일',
    '最近': '최근',
    '昔': '옛날',
}

def translate_line(line):
    """Translate a single line from Japanese to Korean"""
    # Skip header and context lines
    if line.startswith('Found') or line.startswith('---') or line.strip() == '':
        return line

    # For dialogue lines, translate only the text part
    match = re.match(r'(\s*0x[0-9A-F]+\s+\[[^\]]+\]\s+\[script:[^\]]+\])(.+)', line)
    if match:
        prefix = match.group(1)
        text = match.group(2)

        # Replace character/place names
        for jp, kr in CHAR_MAP.items():
            text = text.replace(jp, kr)

        # Apply simple pattern replacements
        for jp, kr in PATTERNS.items():
            text = text.replace(jp, kr)

        return prefix + text

    return line

def main():
    source = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/S800_STG.txt'
    output = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/ko/S800_STG_auto.txt'

    print("Reading source file...")
    with open(source, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"Translating {len(lines)} lines...")
    translated = [translate_line(line) for line in lines]

    print(f"Writing to {output}...")
    with open(output, 'w', encoding='utf-8') as f:
        f.writelines(translated)

    print("Done!")

if __name__ == '__main__':
    main()
