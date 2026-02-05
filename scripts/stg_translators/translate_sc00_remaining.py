#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(_SCRIPT_DIR, "..", "..")  # atl2_korean_translation/

# Translation mappings for Arc the Lad 2
char_names = {
    'エルク': '엘크',
    'リーザ': '리자',
    'シャンテ': '샨테',
    'ポコ': '포코',
    'トッシュ': '토슈',
    'ゴーゲン': '고겐',
    'シュウ': '슈우',
    'ククル': '쿠쿠루',
    'グルガ': '그루가',
    'イーガ': '이가',
    'サニア': '사니아',
    'アーク': '아크',
    'ちょんがら': '총가라',
    'ミリル': '미리르',
}

place_names = {
    'ロマリア': '로말리아',
    'アルディア': '알디아',
    'プロディアス': '프로디아스',
    'インディゴス': '인디고스',
    'スメリア': '스메리아',
    'パレンシア': '팔렌시아',
    'ニーデル': '니델',
    'ブラキア': '브라키아',
}

villain_names = {
    'ガルアーノ': '갈아노',
    'アンデル': '안델',
    'ヤグン': '야군',
    'ゾルコン': '졸콘',
    'クライム': '크라임',
}

# File paths
source_file = os.path.join(BASE_DIR, "output", "decoded", "stg", "SC00_STG.txt")
ko_file = os.path.join(BASE_DIR, "translated", "ko", "SC00_STG.txt")

# Read input file
with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Read what's already translated
with open(ko_file, 'r', encoding='utf-8') as f:
    translated_content = f.read()

# Find where we left off (line 702 approximately)
translated_lines = translated_content.count('\n')
print(f"Already translated: {translated_lines} lines")
print(f"Total lines in source: {len(lines)}")

# Start from line 702 (index 701)
start_line = 701

# Manual translations for remaining content
translations = {
    '私はあなた達を利用しようとしたのよ': '난 너희들을 이용하려 했던 거야',
    '一緒にいくわけにはいかないわ': '함께 갈 수는 없어',
    'おれ達だって\\nそんなに立派な人間じゃない': '우리라고\\n그렇게 훌륭한 인간은 아니야',
    'みんなそれぞれの思いを持って\\n戦っているんだ': '다들 각자의 생각을 갖고\\n싸우고 있는 거야',
    '我が祖国を救ってくれたのだ\\n今度は私がお前を助けよう': '내 조국을 구해줬으니\\n이번엔 내가 너를 도와주마',
    'でけぇな…': '엄청 크네...',
    'あんなもん、\\nどうやって破壊するんだ！？': '저런 걸\\n어떻게 파괴하는 거야!?',
    'なんか、すごくかたそうだね': '뭔가 엄청 단단해 보여',
    'どうやって著に入ろうか？': 'どうやって著に入ろうか？',
    'あんた、頭悪いわねぇ': '너 머리 나쁘구나',
    'わざわざかたい所をねらう\\nバカが、どこにいるの？': '굳이 딱딱한 곳을 노리는\\n바보가 어디 있어?',
    'やわらかい部分を沮えばいいじゃない': '부드러운 부분을 노리면 되잖아',
    'どこなの？[opt]そのやわらかい部分って？': '어디인데?[opt]그 부드러운 부분이?',
    'そうねぇ…私が思うにここかしら？': '글쎄... 내 생각엔 여기일까?',
    'あれだけ大きいのよ、\\n横や下からの攻撃の事は考えていても': '저렇게 큰데\\n옆이나 아래에서의 공격은 생각해도',
    '上から乗り込まれるとは考えてないでしょう': '위에서 침입당할 거라곤 생각 못 했겠지',
    '列車の天じょうか…': '열차 천장인가...',
    'でも、上には対空砲があるよ': '하지만 위엔 대공포가 있잖아',
    '何いってるの、対空砲しかないのよ': '무슨 소리야, 대공포밖에 없다고',
    'その対空砲さえ叩いてしまえば、\\n著に入りこむことができるわ': '그 대공포만 부숴버리면\\n안으로 들어갈 수 있어',
    '飛行船で列車の天じょうにとりつき、\\n内部から列車を破壊するのか': '비행선으로 열차 천장에 붙어서\\n내부에서 열차를 파괴하는 건가',
    'だけど、敵だってバカじゃないぜ': '하지만 적도 바보는 아니라고',
    'そんな簡淡に乗せてくれるわけないだろ？': '그렇게 쉽게 당해줄 리 없잖아?',
    'そうだよ、乗り込む前に\\n列車が逃げちゃうかもしれないし': '그래, 침입하기 전에\\n열차가 도망갈지도 모르고',
    'もちろん、列車の注意を引くのと\\n敵を足止めすることは必要よ': '물론 열차의 주의를 끌고\\n적을 저지하는 건 필요해',
}

print(f"\\nStarting translation from line {start_line + 1}...")

# Append remaining translations
with open(ko_file, 'a', encoding='utf-8') as out:
    for i in range(start_line, len(lines)):
        line = lines[i].rstrip('\\n')

        # Check if it's a dialogue line or context/blank line
        if line.strip() == '' or line.strip().startswith('---'):
            # Keep blank lines and context separators as-is
            out.write(line + '\\n')
        elif line.strip().startswith('0x'):
            # Parse dialogue line
            # Format: "  0xOFFSET [0xOPCODE] [script:XX XX]Japanese text"
            parts = line.split(']', 2)
            if len(parts) >= 3:
                prefix = ']'.join(parts[:2]) + ']'
                japanese_text = parts[2]

                # Translate the Japanese text
                korean_text = japanese_text
                for jp, kr in translations.items():
                    korean_text = korean_text.replace(jp, kr)

                # Apply character name translations
                for jp, kr in char_names.items():
                    korean_text = korean_text.replace(jp, kr)
                for jp, kr in place_names.items():
                    korean_text = korean_text.replace(jp, kr)
                for jp, kr in villain_names.items():
                    korean_text = korean_text.replace(jp, kr)

                out.write(prefix + korean_text + '\\n')
            else:
                # Fallback if parsing fails
                out.write(line + '\\n')
        else:
            # Unknown format, keep as-is
            out.write(line + '\\n')

print("Translation complete!")
