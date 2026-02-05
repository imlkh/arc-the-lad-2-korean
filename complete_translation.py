#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Manual translations from line 703 onwards
manual_translations = [
    ("私はあなた達を利用しようとしたのよ", "난 너희들을 이용하려 했던 거야"),
    ("一緒にいくわけにはいかないわ", "함께 갈 수는 없어"),
    ("おれ達だって\\nそんなに立派な人間じゃない", "우리라고\\n그렇게 훌륭한 인간은 아니야"),
    ("みんなそれぞれの思いを持って\\n戦っているんだ", "다들 각자의 생각을 갖고\\n싸우고 있는 거야"),
    ("我が祖国を救ってくれたのだ\\n今度は私がお前を助けよう", "내 조국을 구해줬으니\\n이번엔 내가 너를 도와주마"),
    ("でけぇな…", "엄청 크네..."),
    ("あんなもん、\\nどうやって破壊するんだ！？", "저런 걸\\n어떻게 파괴하는 거야!?"),
    ("なんか、すごくかたそうだね", "뭔가 엄청 단단해 보여"),
    ("どうやって著に入ろうか？", "どうやって著に入ろうか？"),
    ("あんた、頭悪いわねぇ", "너 머리 나쁘구나"),
    ("わざわざかたい所をねらう\\nバカが、どこにいるの？", "굳이 딱딱한 곳을 노리는\\n바보가 어디 있어?"),
    ("やわらかい部分を沮えばいいじゃない", "부드러운 부분을 노리면 되잖아"),
    ("どこなの？[opt]そのやわらかい部分って？", "어디인데?[opt]그 부드러운 부분이?"),
    ("そうねぇ…私が思うにここかしら？", "글쎄... 내 생각엔 여기일까?"),
    ("あれだけ大きいのよ、\\n横や下からの攻撃の事は考えていても", "저렇게 큰데\\n옆이나 아래에서의 공격은 생각해도"),
    ("上から乗り込まれるとは考えてないでしょう", "위에서 침입당할 거라곤 생각 못 했겠지"),
    ("列車の天じょうか…", "열차 천장인가..."),
    ("でも、上には対空砲があるよ", "하지만 위엔 대공포가 있잖아"),
    ("何いってるの、対空砲しかないのよ", "무슨 소리야, 대공포밖에 없다고"),
    ("その対空砲さえ叩いてしまえば、\\n著に入りこむことができるわ", "그 대공포만 부숴버리면\\n안으로 들어갈 수 있어"),
    ("飛行船で列車の天じょうにとりつき、\\n内部から列車を破壊するのか", "비행선으로 열차 천장에 붙어서\\n내부에서 열차를 파괴하는 건가"),
    ("だけど、敵だってバカじゃないぜ", "하지만 적도 바보는 아니라고"),
    ("そんな簡淡に乗せてくれるわけないだろ？", "그렇게 쉽게 당해줄 리 없잖아?"),
    ("そうだよ、乗り込む前に\\n列車が逃げちゃうかもしれないし", "그래, 침입하기 전에\\n열차가 도망갈지도 모르고"),
    ("もちろん、列車の注意を引くのと\\n敵を足止めすることは必要よ", "물론 열차의 주의를 끌고\\n적을 저지하는 건 필요해"),
    ("二手に分かれて、\\n同時に列車を攻撃するのか…", "둘로 나뉘어서\\n동시에 열차를 공격하는 건가..."),
    ("でも、シルバーノアじゃ大きすぎて\\n天じょうに行く前にすぐ見つかっちゃうよ", "하지만 실버노아는 너무 커서\\n천장에 가기 전에 바로 들키겠어"),
    ("…あんた、いちいち、うるさいわねぇ", "...너 일일이 시끄럽구나"),
    ("ゴ、ゴメンなさ～い", "미, 미안해요~"),
    ("俺のヒエンを使えばいいだろ？", "내 히엔을 쓰면 되잖아?"),
]

# Read the current translated file
with open('/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/ko/SC00_STG.txt', 'r', encoding='utf-8') as f:
    current_content = f.read()

# Read the source file
with open('/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/SC00_STG.txt', 'r', encoding='utf-8') as f:
    source_lines = f.readlines()

# Find how many lines are already translated
current_line_count = current_content.count('\\n')
print(f"Current translated lines: {current_line_count}")
print(f"Total source lines: {len(source_lines)}")

# Append remaining lines with translations
with open('/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/extracted_files/translated/ko/SC00_STG.txt', 'a', encoding='utf-8') as out:
    for i in range(current_line_count, len(source_lines)):
        line = source_lines[i].rstrip()

        # Keep context lines and blank lines as-is
        if not line or line.strip().startswith('---'):
            out.write(line + '\\n')
            continue

        # Process dialogue lines
        if '0x' in line and '[script:' in line:
            # Split into prefix and text
            parts = line.split(']', 2)
            if len(parts) >= 3:
                prefix = ']'.join(parts[:2]) + ']'
                text = parts[2]

                # Apply translations
                translated_text = text
                for jp, kr in manual_translations:
                    translated_text = translated_text.replace(jp, kr)

                # Apply character name translations
                char_names = {
                    'エルク': '엘크', 'リーザ': '리자', 'シャンテ': '샨테',
                    'ポコ': '포코', 'トッシュ': '토슈', 'ゴーゲン': '고겐',
                    'シュウ': '슈우', 'ククル': '쿠쿠루', 'グルガ': '그루가',
                    'イーガ': '이가', 'サニア': '사니아', 'アーク': '아크',
                    'ちょんがら': '총가라', 'ミリル': '미리르', 'ヤグン': '야군',
                    'ガルアーノ': '갈아노', 'アンデル': '안델', 'ゾルコン': '졸콘',
                    'クライム': '크라임', 'ロマリア': '로말리아',
                    'アルディア': '알디아', 'プロディアス': '프로디아스',
                    'インディゴス': '인디고스', 'スメリア': '스메리아',
                    'パレンシア': '팔렌시아', 'ニーデル': '니델',
                    'ブラキア': '브라키아', 'ミルマーナ': '밀마나',
                    'グレイシーヌ': '그레이슈뉴', 'トヨーケ': '토요케',
                    'シルバーノア': '실버노아', 'ニエン': '니엔',
                    'グラウノルン': '그라우노른', 'ギオネス': '기오네스',
                    'ロアン': '로안', 'ロンウィッド・タリスマン': '론위드 탈리스만',
                    'ペイサス': '페이서스', 'アジャール': '아자르',
                    'ラマダ': '라마다', 'ザレフ': '자레프',
                    'ヒエン': '히엔',
                }
                for jp, kr in char_names.items():
                    translated_text = translated_text.replace(jp, kr)

                out.write(prefix + translated_text + '\\n')
            else:
                out.write(line + '\\n')
        else:
            out.write(line + '\\n')

print("Translation appended successfully!")
