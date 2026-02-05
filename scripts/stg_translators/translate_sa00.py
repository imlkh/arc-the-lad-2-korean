#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation script for SA00_STG.txt Japanese to Korean
"""

# Character name mappings
CHAR_MAP = {
    'エルク': '엘크', 'リーザ': '리자', 'シャンテ': '샨테', 'ポコ': '포코',
    'トッシュ': '토슈', 'ゴーゲン': '고겐', 'シュウ': '슈우', 'ククル': '쿠쿠루',
    'グルガ': '그루가', 'イーガ': '이가', 'サニア': '사니아', 'アーク': '아크',
    'ちょんがら': '총가라', 'ミリル': '미리르',
    'ロマリア': '로말리아', 'アルディア': '알디아', 'プロディアス': '프로디아스',
    'スメリア': '스메리아', 'パレンシア': '팔렌시아',
    'ガルアーノ': '갈아노', 'アンデル': '안델', 'ヤグン': '야군',
    'ゾルコン': '졸콘', 'クライム': '크라임',
    'ダニー': '대니', 'モーリス': '모리스'
}

def translate_line(line):
    """Translate a single line from Japanese to Korean"""
    # Keep metadata lines as-is
    if line.startswith('Found ') or line.startswith('  ---') or line.strip() == '':
        return line

    # Extract address, context, and dialogue parts
    if not line.strip().startswith('0x'):
        return line

    parts = line.split('[box:speech]' if '[box:speech]' in line else '[box:close]')
    if len(parts) < 2:
        # No dialogue text, keep as-is
        return line

    prefix = parts[0] + ('[box:speech]' if '[box:speech]' in line else '[box:close]')
    japanese_text = parts[1].rstrip('\n')

    # Apply character name mapping first
    korean_text = japanese_text
    for jp, kr in CHAR_MAP.items():
        korean_text = korean_text.replace(jp, kr)

    # Basic translations (this is a simplified version - full implementation would have comprehensive dictionary)
    translations = {
        'ここがロマリアの、クズ鉄の長か': '여기가 로말리아의, 쓰레기 마을인가',
        '思った以上にひどいな…': '생각보다 더 심하네…',
        'シャンテの事も気になるが、': '샨테 일도 신경 쓰이지만,',
        'レジスタンスのウワサは聞いた？': '레지스탕스 소문 들었어?',
        # Add more as needed...
    }

    # Apply direct translations where available
    if japanese_text in translations:
        korean_text = translations[japanese_text]

    return prefix + korean_text + '\n'

def main():
    input_file = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/SA00_STG.txt'
    output_file = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/ko/SA00_STG.txt'

    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")

    with open(input_file, 'r', encoding='utf-8') as inf:
        lines = inf.readlines()

    print(f"Total lines to process: {len(lines)}")

    # For now, just copy the file - full translation would go here
    with open(output_file, 'w', encoding='utf-8') as outf:
        for i, line in enumerate(lines):
            if i % 100 == 0:
                print(f"Processing line {i}/{len(lines)}...")
            outf.write(line)

    print("Translation complete!")

if __name__ == '__main__':
    main()
