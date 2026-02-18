#!/usr/bin/env python3
"""Fix truncated STG translation strings that overflow their fixed-length slots.

Applies verified shortenings to all affected STG files:
- Group A: 5 common dungeon UI strings (~70 instances across stages)
- Group B: Unique dialogue lines (~18 instances in specific stages)
"""
import re
from pathlib import Path

TRANSLATED_DIR = Path(__file__).parent.parent.parent / "translated" / "ko"

# Group A: Common UI string replacements (content after [script:XX XX])
# Maps old content -> new content (without [box:system] prefix which stays)
GROUP_A = [
    # Switch variants
    (r'\[box:system\]스위치가 있습니다\[br\]ON으로 하시겠습니까\?\[br\]\[opt\]예\[br\]\[opt\]아니오\[box:close\]',
     '[box:system]스위치 발견[br]ON할까?[br][opt]네[br][opt]아니오[box:close]'),
    (r'\[box:system\]스위치가 있습니다\[br\]ON으로 해보시겠습니까\?\[br\]\[opt\]예\[br\]\[opt\]아니오\[box:close\]',
     '[box:system]스위치 발견[br]ON할까?[br][opt]네[br][opt]아니오[box:close]'),
    (r'\[box:system\]스위치가 있습니다\[br\]ON으로 해볼까요\?\[br\]\[opt\]네\[br\]\[opt\]아니오\[box:close\]',
     '[box:system]스위치 발견[br]ON할까?[br][opt]네[br][opt]아니오[box:close]'),
    # Down stairs
    (r'\[box:system\]내려가는 계단이 있습니다\[br\]\[opt\]내려간다\[br\]\[opt\]그만둔다\[box:close\]',
     '[box:system]계단 발견[br][opt]내려가기[br][opt]그만두기[box:close]'),
    # Up stairs
    (r'\[box:system\]올라가는 계단이 있습니다\[br\]\[opt\]올라간다\[br\]\[opt\]그만둔다\[box:close\]',
     '[box:system]계단 발견[br][opt]올라가기[br][opt]그만두기[box:close]'),
    # Exit variants
    (r'\[box:system\]출구입니다\. 밖으로 나가시겠습니까\?\[br\]\[opt\]예\[br\]\[opt\]아니오\[box:close\]',
     '[box:system]출구다. 나갈까?[br][opt]네[br][opt]아니오[box:close]'),
    (r'\[box:system\]출구입니다\. 밖으로 나갈까요\?\[br\]\[opt\]네\[br\]\[opt\]아니오\[box:close\]',
     '[box:system]출구다. 나갈까?[br][opt]네[br][opt]아니오[box:close]'),
    # Ladder
    (r'\[box:system\]사다리가 있습니다\[br\]\[opt\]올라간다\[br\]\[opt\]그만둔다\[box:close\]',
     '[box:system]사다리다[br][opt]올라가기[br][opt]그만두기[box:close]'),
]

# Group B: Unique dialogue replacements (by offset prefix)
# Maps (filename_prefix, offset_hex) -> (old_content_substring, new_content)
GROUP_B = {
    # S500 L412
    ('S500', '0x002E9180'): ('이 사막을 동쪽으로 가면[br]북쪽으로 빠지는 지름길이 있었을 거다',
                             '이 사막 동쪽으로 가면[br]북쪽 지름길이 있었을 거다'),
    # S600 L483 - noise text
    ('S600', '0x0050C0C0'): ('<노이즈 텍스트>', '…'),
    # S700 L3997
    ('S700', '0x018FD862'): ('쿠쿠루, 이 녀석을 좀 치료해 주겠나', '쿠쿠루, 이 녀석 치료해주겠나'),
    # S700 L3999
    ('S700', '0x018FD8AC'): ('그럼, 이쪽으로 옮겨 주세요…', '옮겨주세요…'),
    # S700 L4041
    ('S700', '0x018FE786'): ('그럼, 이쪽으로 옮겨 주세요…', '옮겨주세요…'),
    # S700 L4087
    ('S700', '0x018FFDFE'): ('[opt]그렇게 하겠다[br][opt]다시 생각해 본다', '[opt]좋다[br][opt]생각해본다'),
    # S700 L4097
    ('S700', '0x01900042'): ('쿠쿠루, 이걸로 괜찮겠나?', '쿠쿠루, 됐나?'),
    # S700 L4099
    ('S700', '0x01900082'): ('네, 분명 괜찮을 거예요, 저분들이라면…', '네, 괜찮을 거예요…'),
    # S700 L4104
    ('S700', '0x0190027A'): ('엘크는 살아날 수 있어요?', '엘크 살아나요?'),
    # S700 L4105
    ('S700', '0x019002BC'): ('이제 그 사람에게 달렸다고밖엔…', '그 사람 달렸다고…'),
    # SA00 L896
    ('SA00', '0x00462538'): ('[box:speech]순조롭게 진행 중입니다', '[box:speech]순조로이 진행중'),
    # SA00 L904
    ('SA00', '0x00462654'): ('[box:speech]그럼 들어오시죠', '[box:speech]오시죠'),
    # SE00 L862
    ('SE00', '0x00753464'): ('뭐야! 이 정도쯤이야', '뭐! 이 정도야'),
    # SE00 L870
    ('SE00', '0x007535A8'): ('기 센 것도 좋지만,[br]목숨을 함부로 쓰진 마라', '기 센 건 좋지만[br]목숨 함부로 쓰지 마'),
    # SE00 L882
    ('SE00', '0x00753758'): ('쓸데없는 짓은 안 했으면 좋겠네', '쓸데없는 짓 좀 그만해'),
    # SE00 L927
    ('SE00', '0x00753D90'): ('정말 고집불통이네!', '고집쟁이!'),
    # SG00 L143
    ('SG00', '0x002E8DDE'): ('지상으로 돌아가겠습니까?[br][opt]아니오[br][opt]네', '돌아갈까?[br][opt]아니오[br][opt]네'),
    # SG00 L297
    ('SG00', '0x0051CF2E'): ('어떡하지, 분명 함정이야', '어떡해, 함정이다!'),
    # SG00 L328
    ('SG00', '0x0051DB42'): ('순순히 바람의 오브를 내놔!', '바람의 오브 내놔!'),
    # SG00 L335
    ('SG00', '0x0051E74C'): ('이제 마을 사람들도 원래대로 돌아오겠지', '이제 마을사람도 돌아오겠지'),
    # SG00 L347
    ('SG00', '0x0051E9D8'): ('바람의 정령이여', '정령이여'),
    # SG00 L352
    ('SG00', '0x0051EAC6'): ('부탁드립니다, 저에게 힘을 빌려주세요', '부탁합니다, 힘을 빌려주세요'),
    # SG00 L355
    ('SG00', '0x0051EB82'): ('무시무시한 일을 꾸미고 있을지도 모른다', '무서운 짓을 꾸미고 있을지도'),
    # SF00 L736
    ('SF00', '0x0051C632'): ('[box:speech]이봐, 오히려 몬스터한테 당하면[br]어쩌자는 거야',
                             '[box:speech]이봐, 몬스터한테 당하면[br]어쩌자는 거야'),
    # SF00 L767
    ('SF00', '0x0051D252'): ('[box:speech]정말, 금방[br]삐치고 말이야…', '[box:speech]정말 금방[br]삐치니…'),
    # SF00 L786
    ('SF00', '0x0051D5E2'): ('싶었으니까 말이야', '싶었으니까'),
    # SF00 L792
    ('SF00', '0x0051D71A'): ('[box:speech]내겐 쓸 수 있는 돈이 좀 있고,[br]마을에 도움이 된다면 좋겠다고 생각했지',
                             '[box:speech]내겐 쓸 돈이 좀 있고[br]마을에 도움되면 좋겠다 생각했지'),
}


def fix_file(filepath):
    """Apply fixes to a single STG translation file."""
    stage = filepath.stem.replace('_STG', '')
    with open(filepath) as f:
        lines = f.readlines()

    changes = 0

    # Apply Group A replacements
    for i, line in enumerate(lines):
        for pattern, replacement in GROUP_A:
            if re.search(pattern, line):
                new_line = re.sub(pattern, replacement, line)
                if new_line != lines[i]:
                    lines[i] = new_line
                    changes += 1
                break

    # Apply Group B replacements
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith('0x'):
            continue
        offset = stripped.split()[0]
        key = (stage, offset)
        if key in GROUP_B:
            old_sub, new_sub = GROUP_B[key]
            if old_sub in line:
                lines[i] = line.replace(old_sub, new_sub)
                changes += 1

    if changes:
        with open(filepath, 'w') as f:
            f.writelines(lines)

    return changes


def main():
    total = 0
    for stg_file in sorted(TRANSLATED_DIR.glob('*_STG.txt')):
        n = fix_file(stg_file)
        if n:
            print(f"  {stg_file.stem}: {n} fixes applied")
            total += n

    print(f"\nTotal: {total} fixes applied across all STG files")


if __name__ == '__main__':
    main()
