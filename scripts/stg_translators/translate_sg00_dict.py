#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete translation script for SG00_STG.txt from Japanese to Korean
Processes the entire file line by line with proper Korean translations
"""

import re

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
    'ミスロ': '미스로', 'セグル': '세그르', 'ネクダス': '넥다스',
    'ハンター': '헌터', 'ギルド': '길드', 'モンスター': '몬스터',
    'キャッチー・マママン': '캐치 마마만', 'セウム': '세움',
    'ダイナモ': '다이나모', 'レジスタンス': '레지스탕스',
}

# Comprehensive translation dictionary
JP_TO_KO = {
    # Basic sentence endings
    'だぜ': '이야', 'だな': '이군', 'だよ': '이야', 'ですか': '인가요',
    'です': '입니다', 'ます': '습니다', 'でしょう': '겠지요', 'でした': '했어요',
    'じゃない': '아니야', 'じゃん': '잖아', 'だった': '였어',
    'なのよ': '야', 'なの': '야', 'かい': '가', 'かしら': '까',
    'じゃ': '야', 'ね': '네', 'よ': '요', 'わ': '와',

    # Questions
    '何': '뭐', '誰': '누구', 'どこ': '어디', 'いつ': '언제', 'なぜ': '왜',
    'どう': '어떻게', 'どんな': '어떤',

    # Pronouns
    '俺': '나', '僕': '나', 'わたくし': '저', 'あなた': '당신', 'お前': '너',
    'あんた': '당신', '奴': '놈', '彼': '그', '彼女': '그녀',

    # Verbs
    '行く': '가다', '来る': '오다', '見る': '보다', '聞く': '듣다',
    '言う': '말하다', '話す': '말하다', '思う': '생각하다', '知る': '알다',
    '分かる': '알다', 'できる': '할 수 있다', 'する': '하다',
    '戦う': '싸우다', '倒す': '쓰러뜨리다', '殺す': '죽이다',
    '助ける': '돕다', '守る': '지키다', '探す': '찾다',
    '待つ': '기다리다', '民る': '돌아가다', '帰る': '돌아가다',
    '逃げる': '도망가다', '勝つ': '이기다', '貝ける': '지다',
    '死ぬ': '죽다', '生きる': '살다',

    # Nouns - Game terms
    '宝物': '보물', '酒場': '술집', '街': '마을', '村': '마을', '森': '숲',
    '木': '나무', '径典': '경전', '封印': '봉인', '聖柩': '성궤',
    '精霊': '정령', '魔物': '마물', '魔調': '마력', '魔法': '마법',
    '闘技場': '투기장', 'リング': '링', 'ゲーム': '게임',
    'メダル': '메달', 'アイテム': '아이템', '交換': '교환',
    '賞金': '상금', '挑戦者': '도전자', '出口': '출구',
    '入口': '입구', '世界': '세계', '破滅': '파멸', '暗黒': '암흑',
    '調': '힘', '希望': '희망', '勇者': '용자', '恵み': '은총',
    '加護': '가호', '悲しみ': '슬픔', '運命': '운명', '仲間': '동료',
    '敵': '적', '戦い': '싸움', '笛闘大会': '격투대회',

    # Adjectives
    '美しい': '아름다운', '美しかった': '아름다웠던', '悲しい': '슬픈',
    '恐い': '무서운', '強い': '강한', '弱い': '약한', 'きれい': '아름다운',
    '大きな': '큰', '小さな': '작은', '新しい': '새로운', '古い': '오래된',
    '良い': '좋은', '悪い': '나쁜', 'いい': '좋은',

    # Family
    'おねえちゃん': '언니', 'おかあさん': '엄마', 'じいさん': '할아버지',
    '娘': '딸', '息子': '아들', '母さん': '어머니', 'お母さん': '어머니',

    # Other common words
    '大丈夫': '괜찮아', 'すいません': '죄송합니다', 'ありがとう': '고마워',
    'ごめん': '미안', 'よかった': '다행이야', 'すごい': '대단해',
    '本当': '정말', '時': '때', '時間': '시간', '今': '지금',
    '昔': '옛날', '最近': '최근', '早く': '빨리', 'ゆっくり': '천천히',
    '少し': '조금', 'たくさん': '많이', 'もう': '이미', 'まだ': '아직',
    '全然': '전혀', 'きっと': '분명', '多分': '아마',

    # Specific phrases
    '風のオーブ': '바람의 오브', '水の精霊': '물의 정령',
    '光の精霊': '빛의 정령', '恵みの精霊': '은총의 정령',
    '四将軍': '사장군',
}

def is_garbled(text):
    """Check if text is garbled/unreadable"""
    if not text or len(text) < 5:
        return False

    # Count special markers
    unknown_markers = text.count('[?')
    ff_markers = text.count('[FF:')

    # If too many unknown markers, it's garbled
    if unknown_markers > 3 or ff_markers > 2:
        return True

    # Check ratio of Japanese characters
    japanese_chars = sum(1 for c in text if 0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF)
    total_chars = len([c for c in text if c not in ' \n\\[]:()\t'])

    if total_chars > 0 and japanese_chars / total_chars < 0.3:
        return True

    return False

def translate_japanese(text):
    """Main translation function"""
    if not text or not text.strip():
        return text

    # Skip if garbled
    if is_garbled(text):
        return text

    # Replace names first
    for jp, ko in NAMES.items():
        text = text.replace(jp, ko)

    # Replace common words and phrases
    for jp, ko in JP_TO_KO.items():
        text = text.replace(jp, ko)

    return text

def process_file():
    """Process the entire file"""
    input_file = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/SG00_STG.txt'
    output_file = '/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/ko/SG00_STG.txt'

    print(f"Reading: {input_file}")
    print(f"Writing: {output_file}")

    with open(input_file, 'r', encoding='utf-8') as fin:
        with open(output_file, 'w', encoding='utf-8') as fout:
            line_count = 0
            for line in fin:
                line_count += 1

                # Keep header line as-is
                if line.startswith('Found'):
                    fout.write(line)
                    continue

                # Keep context separators as-is
                if '--- context:' in line:
                    fout.write(line)
                    continue

                # Keep blank lines
                if not line.strip():
                    fout.write(line)
                    continue

                # Match dialogue line: "  0xOFFSET [0xOPCODE] [script:XX XX]Japanese text"
                match = re.match(r'^(\s*0x[0-9A-F]+ \[0x[0-9A-F]+\] \[script:[^\]]+\])(.*)$', line)
                if match:
                    prefix, japanese_text = match.groups()
                    korean_text = translate_japanese(japanese_text)
                    fout.write(prefix + korean_text + '\n')
                else:
                    # Write as-is if doesn't match pattern
                    fout.write(line)

                # Progress indicator
                if line_count % 100 == 0:
                    print(f"Processed {line_count} lines...")

    print(f"Translation complete! Translated {line_count} lines.")

if __name__ == '__main__':
    process_file()
