#!/usr/bin/env python3
"""
Auto-fill BEAM.DAT duplicate translations and apply manual translations.

Strategy:
1. Build garbled→Korean mapping from existing 176 translated entries
2. Auto-fill duplicate system messages (1,033 entries)
3. Apply manual translations for 51 unique untranslated entries
4. Write updated translation file
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "..")
TRANSLATION_FILE = os.path.join(PROJECT_DIR, "translated", "ko", "BEAM_DAT.txt")
DECODED_FILE = os.path.join(PROJECT_DIR, "output", "decoded", "bin", "BEAM_DAT.txt")

ENTRY_RE = re.compile(r'  (0x[0-9A-Fa-f]+) \[\s*(\d+)\] (.*)')


def strip_box_tags(text):
    """Remove [box:system], [box:speech], [box:narration], [box:close] tags."""
    text = text.replace("[box:system]", "")
    text = text.replace("[box:speech]", "")
    text = text.replace("[box:narration]", "")
    text = text.replace("[box:close]", "")
    return text


# Manual translations for the 51 unique untranslated entries
# Key: garbled Japanese text (with box tags, as it appears in decoded file)
# Value: Korean translation (WITHOUT box tags)
MANUAL_TRANSLATIONS = {
    # 1. Narration - Choko scene
    "[box:narration]ちょこ、どうしたんだ！":
        "ちょこ、どうしたんだ！",  # Keep as Japanese name + exclamation → translate below

    # 2. System - character selection
    "[box:system]集総に琥惜するキャラクターを[br]獣んで告さい[box:close]":
        "선두에 참가할 캐릭터를[br]골라 주세요",

    # 3. Debug flag (error message)
    "[box:speech]クズ先フラグ[opt]エラーです[br][opt]＠ロマリアトンネル2♦":
        "쿠즈사키 플래그[opt]에러입니다[br][opt]＠로마리아터널2♦",

    # 4-10. Battle dialogue - Danny's escape scene
    "[box:speech]はやく！[opt]はやく！":
        "빨리![opt]빨리!",

    "[box:speech]ざんねんだが、そこまでだぜ":
        "안됐지만, 여기까지다",

    "[box:speech]ここからは、相がしゃしねぇよ":
        "여기서부터는, 도망칠 수 없다",

    "[box:speech]相げろ、ダニー！":
        "도망쳐, 대니!",

    "[box:speech]でも…":
        "하지만…",

    "[box:speech]いいから、係け！":
        "됐으니까, 뛰어!",

    "[box:speech]ちくしょう！":
        "젠장!",

    # 11-12. Battle aftermath
    "[box:speech]おい、撤っておきな":
        "이봐, 물러서 있어",

    "[box:speech]これで…[delay:15]よしと":
        "이것으로…[delay:15]됐다",

    # 13-23. Confrontation with Galahno's men
    "[box:speech]お重が、ガルアーノ孤を牲って[br]きたという、ハンターか":
        "네놈이, 가루아노님을 쫓아[br]왔다는, 헌터인가",

    "[box:speech]なるほど、バカっぽい[br]果をしてやがるぜ":
        "과연, 바보 같은[br]얼굴을 하고 있군",

    "[box:speech]なんだと！？":
        "뭐라고!?",

    "[box:speech]おいおい、囲るなよ":
        "이봐이봐, 화내지 마",

    "[box:speech]鍵皇されているのもわからねぇんじゃ、[br]そう緊われてもしょうがねぇよなぁ":
        "바보 취급당하는 것도 모르겠다면,[br]그렇게 불려도 어쩔 수 없지",

    "[box:speech]ここで、お重らをぶっ故せば、[br]のこるはザコばかりだからな":
        "여기서, 너희들을 해치우면,[br]남는 건 잡졸뿐이니까",

    "[box:speech]これで演も、ガルアーノ孤に[br]おぼえがいいってもんよ":
        "이걸로 나도, 가루아노님께[br]인정받겠지",

    "[box:speech]ごちゃごちゃ緊ってねぇで、[br]かかってきやがれ！":
        "쓸데없이 지껄이지 말고,[br]덤벼라!",

    "[box:speech]そう、せかすなよ":
        "그렇게 재촉하지 마",

    "[box:speech]こちらも、属刀がそろったことだし、":
        "이쪽도, 동료가 모였으니,",

    "[box:speech]お伝み精り、向めてやるよ！":
        "바라는 대로, 시작해 주지!",

    # 24-31. Mid-battle dialogue
    "[box:speech]くそっ！":
        "젠장!",

    "[box:speech]握らは堅札から、演のことに[br]館づいていたのか！":
        "놈들은 처음부터, 내게[br]눈치채고 있었단 말인가!",

    "[box:speech]演が、レジスタンスに陣づく[br]ことを墟語していて…":
        "내가 레지스탕스에 접근하는[br]것을 경계하고 있었어…",

    "[box:speech]却やむのは嫌にしろ！":
        "쓰러지는 건 아직 이르다!",

    "[box:speech]寒がねぇと、属刀が神ない！！":
        "서두르지 않으면, 동료가 올 수 없어!!",

    "[box:speech]こんなところでグズグズ[br]していられねぇぞ！":
        "이런 곳에서 꾸물거리고[br]있을 수 없다고!",

    "[box:speech]循くアジトに殴らねぇと！":
        "빨리 아지트로 돌아가야 해!",

    "[box:speech]そうだな":
        "그래",

    "[box:speech]そろそろ、いいかな":
        "슬슬, 되었을까",

    # 33. Breathing
    "[box:speech]はぁ、はぁ":
        "하아, 하아",

    # 34-38. Battle taunts
    "[box:speech]おいおい、そんなに蓄れちまって[br]集えるのかい？":
        "이봐이봐, 그렇게 지치고[br]싸울 수 있겠어?",

    "[box:speech]いい館になるなよ！[br][delay:15]…はぁはぁ":
        "잘난 체하지 마![br][delay:15]…하아하아",

    "[box:speech]憶らの須、協せてやるわ！":
        "우리의 힘을 보여주겠다!",

    "[box:speech]ふっふっふっ、":
        "후후후,",

    "[box:speech]きさまを敵らえ、憶が絵への[br]跡みやげとしてくれる！":
        "네놈을 사로잡아, 윗분에게[br]바칠 선물로 삼아주지!",

    # 39-44. Strategy discussion
    "[box:speech]なんでもいいから、向めようぜ":
        "뭐든 좋으니까, 시작하자",

    "[box:speech]なるべく坑刀をかせぐ、か…":
        "되도록 시간을 벌어야 한다, 라…",

    "[box:speech]内祖くせぇこといいやがって…":
        "귀찮은 소리 하고 있어…",

    "[box:speech]更にそうになったら、とっとと[br]相げるが…[delay:15]うらむんじゃねぇぞ！":
        "위험해지면, 재빨리[br]도망치겠지만…[delay:15]원망하지 마라!",

    "[box:speech]空をゴチャゴチャ緊っておる！":
        "뭘 쓸데없이 지껄이느냐!",

    "[box:speech]では係くぞ！！":
        "자, 간다!!",

    # 45-49. Battle resolution
    "[box:speech]おうっ！！":
        "오!!",

    "[box:speech]これだけ坑刀をかせげば[br]場私墜だろう":
        "이만큼 시간을 벌었으면[br]충분하겠지",

    "[box:speech]あとは、シュウの交講だな":
        "나머지는, 슈의 교섭에 달렸군",

    "[box:speech]やったぜ！[opt][delay:15]言集社首だ！！":
        "해냈다![opt][delay:15]전원 무사하다!!",

    "[box:speech]怒だけが次抱するチャンスだ！[br][delay:15]寒げ！！":
        "지금만이 탈출할 기회다![br][delay:15]서둘러!!",

    # 50-51. System - Wanted monsters
    "[box:system][opt][opt][opt]跡縦モンスター♣沙伐の信[box:close]":
        "[opt][opt][opt]수배 몬스터♣사막의 주인",

    "[box:system][opt][opt][opt][opt]跡縦モンスター♣キバ[box:close]":
        "[opt][opt][opt][opt]수배 몬스터♣키바",
}

# Fix entry 1: translate the narration properly
MANUAL_TRANSLATIONS["[box:narration]ちょこ、どうしたんだ！"] = "초코, 무슨 일이야!"


def main():
    # Read decoded file to build offset → garbled text mapping
    decoded_map = {}  # offset → garbled text
    with open(DECODED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = ENTRY_RE.match(line.rstrip())
            if m:
                decoded_map[m.group(1)] = m.group(3)

    # Read translation file
    with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:
        trans_lines = f.readlines()

    # Build garbled→Korean mapping from existing translations
    garbled_to_korean = {}
    for line in trans_lines:
        m = ENTRY_RE.match(line.rstrip())
        if not m:
            continue
        offset, length, text = m.group(1), int(m.group(2)), m.group(3)
        has_korean = any('\uac00' <= c <= '\ud7a3' for c in text)
        if has_korean:
            garbled = decoded_map.get(offset)
            if garbled and garbled not in garbled_to_korean:
                garbled_to_korean[garbled] = text

    # Add manual translations
    for garbled, korean in MANUAL_TRANSLATIONS.items():
        garbled_to_korean[garbled] = korean

    print(f"Total garbled→Korean mappings: {len(garbled_to_korean)}")
    print(f"  From existing translations: {len(garbled_to_korean) - len(MANUAL_TRANSLATIONS)}")
    print(f"  From manual translations: {len(MANUAL_TRANSLATIONS)}")

    # Process translation file: replace untranslated entries
    new_lines = []
    auto_filled = 0
    manual_filled = 0
    still_untranslated = 0

    for line in trans_lines:
        m = ENTRY_RE.match(line.rstrip())
        if not m:
            new_lines.append(line)
            continue

        offset, length, text = m.group(1), int(m.group(2)), m.group(3)
        has_korean = any('\uac00' <= c <= '\ud7a3' for c in text)

        if has_korean:
            # Already translated - keep as-is
            new_lines.append(line)
            continue

        # Untranslated - try to find Korean translation
        garbled = decoded_map.get(offset, text)

        if garbled in garbled_to_korean:
            korean = garbled_to_korean[garbled]
            new_line = f"  {offset} [{length:4d}] {korean}\n"
            new_lines.append(new_line)
            if garbled in MANUAL_TRANSLATIONS:
                manual_filled += 1
            else:
                auto_filled += 1
        else:
            # Still untranslated
            new_lines.append(line)
            still_untranslated += 1
            print(f"  WARNING: No translation for {offset}: {garbled[:60]}...")

    # Write updated file
    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"\nResults:")
    print(f"  Auto-filled (duplicates): {auto_filled}")
    print(f"  Manual translations: {manual_filled}")
    print(f"  Still untranslated: {still_untranslated}")
    print(f"  Total entries now translated: {176 + auto_filled + manual_filled}")


if __name__ == "__main__":
    main()
