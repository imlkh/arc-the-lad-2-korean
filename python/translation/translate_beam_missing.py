#!/usr/bin/env python3
"""Generate Korean translations for missing BEAM.DAT entries.

Strategy:
1. Cross-reference with SCPS decoded/translated for identical Japanese text
2. Transliterate pure katakana entries to Korean
3. Use known garbled kanji mappings from decode_beam_items.py MANUAL_KO
4. Detect location name patterns (town + suffix)
5. Handle menu/UI labels, skill names, movie names, etc.

Output: new translation entries in format "  0xOFFSET [SIZE] korean_text"
"""

import os
import re
import sys
import unicodedata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))

DECODED_PATH = os.path.join(PROJECT_DIR, "output", "decoded", "bin", "BEAM_DAT.txt")
TRANSLATED_PATH = os.path.join(PROJECT_DIR, "translated", "ko", "BEAM_DAT.txt")
SCPS_DECODED_PATH = os.path.join(PROJECT_DIR, "output", "decoded", "bin", "SCPS_100_26.txt")
SCPS_KO_PATH = os.path.join(PROJECT_DIR, "translated", "ko", "SCPS_100_26.txt")

LINE_RE = re.compile(r'^\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')

# ============================================================
# Katakana -> Korean transliteration tables
# ============================================================

# Basic katakana mapping
KATAKANA_MAP = {
    'ア': '아', 'イ': '이', 'ウ': '우', 'エ': '에', 'オ': '오',
    'カ': '카', 'キ': '키', 'ク': '쿠', 'ケ': '케', 'コ': '코',
    'サ': '사', 'シ': '시', 'ス': '스', 'セ': '세', 'ソ': '소',
    'タ': '타', 'チ': '치', 'ツ': '츠', 'テ': '테', 'ト': '토',
    'ナ': '나', 'ニ': '니', 'ヌ': '누', 'ネ': '네', 'ノ': '노',
    'ハ': '하', 'ヒ': '히', 'フ': '후', 'ヘ': '헤', 'ホ': '호',
    'マ': '마', 'ミ': '미', 'ム': '무', 'メ': '메', 'モ': '모',
    'ヤ': '야', 'ユ': '유', 'ヨ': '요',
    'ラ': '라', 'リ': '리', 'ル': '루', 'レ': '레', 'ロ': '로',
    'ワ': '와', 'ヲ': '오', 'ン': 'ㄴ',
    'ガ': '가', 'ギ': '기', 'グ': '구', 'ゲ': '게', 'ゴ': '고',
    'ザ': '자', 'ジ': '지', 'ズ': '즈', 'ゼ': '제', 'ゾ': '조',
    'ダ': '다', 'ヂ': '지', 'ヅ': '즈', 'デ': '데', 'ド': '도',
    'バ': '바', 'ビ': '비', 'ブ': '부', 'ベ': '베', 'ボ': '보',
    'パ': '파', 'ピ': '피', 'プ': '프', 'ペ': '페', 'ポ': '포',
}

# Small kana for combination sounds
SMALL_KANA = {
    'ャ': 'ya', 'ュ': 'yu', 'ョ': 'yo',
    'ァ': 'a', 'ィ': 'i', 'ゥ': 'u', 'ェ': 'e', 'ォ': 'o',
}

# Korean jamo decomposition helpers
# Initial consonants (초성)
INITIALS = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
            'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
# Medial vowels (중성)
MEDIALS = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
           'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
# Final consonants (종성)
FINALS = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
          'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
          'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# Vowel mapping for small kana combinations
VOWEL_MAP = {
    'a': 'ㅏ', 'i': 'ㅣ', 'u': 'ㅜ', 'e': 'ㅔ', 'o': 'ㅗ',
    'ya': 'ㅑ', 'yu': 'ㅠ', 'yo': 'ㅛ',
}

# Korean vowels (medial)
KR_VOWELS = {
    'ㅏ': 0, 'ㅐ': 1, 'ㅑ': 2, 'ㅒ': 3, 'ㅓ': 4, 'ㅔ': 5, 'ㅕ': 6,
    'ㅖ': 7, 'ㅗ': 8, 'ㅘ': 9, 'ㅙ': 10, 'ㅚ': 11, 'ㅛ': 12,
    'ㅜ': 13, 'ㅝ': 14, 'ㅞ': 15, 'ㅟ': 16, 'ㅠ': 17, 'ㅡ': 18,
    'ㅢ': 19, 'ㅣ': 20,
}


def decompose_hangul(ch):
    """Decompose a Hangul character into (initial, medial, final) jamo indices."""
    code = ord(ch) - 0xAC00
    if code < 0 or code >= 11172:
        return None
    initial = code // (21 * 28)
    medial = (code % (21 * 28)) // 28
    final = code % 28
    return initial, medial, final


def compose_hangul(initial_idx, medial_idx, final_idx=0):
    """Compose a Hangul character from jamo indices."""
    code = 0xAC00 + initial_idx * 21 * 28 + medial_idx * 28 + final_idx
    return chr(code)


def add_final_consonant(ch, final_jamo):
    """Add a final consonant to a Hangul syllable."""
    decomp = decompose_hangul(ch)
    if decomp is None:
        return ch + final_jamo
    initial, medial, _ = decomp
    final_idx = FINALS.index(final_jamo) if final_jamo in FINALS else 0
    return compose_hangul(initial, medial, final_idx)


def change_vowel(ch, new_vowel):
    """Change the vowel of a Hangul syllable."""
    decomp = decompose_hangul(ch)
    if decomp is None:
        return ch
    initial, _, final = decomp
    new_medial = KR_VOWELS.get(new_vowel, 0)
    return compose_hangul(initial, new_medial, final)


def transliterate_katakana(text):
    """Transliterate katakana text to Korean.

    Handles:
    - Basic katakana → Korean syllable mapping
    - Small kana combinations (シャ→샤, チョ→쵸, etc.)
    - ー (long vowel mark) → usually omit or kept
    - ッ (double consonant) → doubles next consonant (written as ㅅ batchim)
    """
    result = []
    i = 0
    chars = list(text)

    while i < len(chars):
        ch = chars[i]

        # Handle long vowel mark ー
        if ch == 'ー':
            # Usually omitted in Korean transliteration
            # But sometimes doubled - we'll just skip it
            i += 1
            continue

        # Handle small tsu ッ (geminate)
        if ch == 'ッ':
            # Add ㅅ as batchim to previous syllable if possible,
            # otherwise store for next
            if result:
                prev = result[-1]
                decomp = decompose_hangul(prev)
                if decomp and decomp[2] == 0:  # no final consonant
                    # Check what the next consonant is
                    if i + 1 < len(chars) and chars[i + 1] in KATAKANA_MAP:
                        next_ko = KATAKANA_MAP[chars[i + 1]]
                        next_decomp = decompose_hangul(next_ko)
                        if next_decomp:
                            # Get the initial consonant of the next syllable
                            next_initial = INITIALS[next_decomp[0]]
                            # Use that consonant as batchim if possible
                            if next_initial in FINALS:
                                result[-1] = add_final_consonant(prev, next_initial)
                                i += 1
                                continue
                    # Default: add ㅅ batchim
                    result[-1] = add_final_consonant(prev, 'ㅅ')
            i += 1
            continue

        # Handle small kana combinations
        if i + 1 < len(chars) and chars[i + 1] in SMALL_KANA:
            base_ko = KATAKANA_MAP.get(ch)
            if base_ko:
                small = SMALL_KANA[chars[i + 1]]
                decomp = decompose_hangul(base_ko)
                if decomp:
                    initial_idx = decomp[0]
                    new_vowel = VOWEL_MAP.get(small)
                    if new_vowel and new_vowel in KR_VOWELS:
                        new_medial = KR_VOWELS[new_vowel]
                        combined = compose_hangul(initial_idx, new_medial, 0)
                        result.append(combined)
                        i += 2
                        continue
            # Fallback: just transliterate both
            if base_ko:
                result.append(base_ko)
            i += 1
            continue

        # Handle ン (n) - special: adds ㄴ batchim to previous syllable
        if ch == 'ン':
            if result:
                prev = result[-1]
                decomp = decompose_hangul(prev)
                if decomp and decomp[2] == 0:
                    result[-1] = add_final_consonant(prev, 'ㄴ')
                    i += 1
                    continue
            # Standalone ン
            result.append('은')
            i += 1
            continue

        # Basic katakana mapping
        if ch in KATAKANA_MAP:
            result.append(KATAKANA_MAP[ch])
            i += 1
            continue

        # Pass through non-katakana characters
        result.append(ch)
        i += 1

    return ''.join(result)


def is_katakana(ch):
    """Check if a character is katakana."""
    cp = ord(ch)
    return 0x30A0 <= cp <= 0x30FF


def is_hiragana(ch):
    """Check if a character is hiragana."""
    cp = ord(ch)
    return 0x3040 <= cp <= 0x309F


def is_kanji(ch):
    """Check if a character is a CJK ideograph."""
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF


def is_pure_katakana(text):
    """Check if text is purely katakana (plus long vowel mark and small tsu)."""
    for ch in text:
        if ch in ('ー', 'ッ'):
            continue
        if ch in SMALL_KANA:
            continue
        if not is_katakana(ch):
            return False
    return len(text) > 0


def strip_control_codes(text):
    """Remove control codes like [box:...], [br], [opt], [FF:...], [delay:...] etc."""
    clean = re.sub(r'\[box:\w+\]', '', text)
    clean = clean.replace('[box:close]', '')
    clean = clean.replace('[br]', '')
    clean = clean.replace('[opt]', '')
    clean = re.sub(r'\[FF:[0-9A-Fa-f ]+\]', '', clean)
    clean = re.sub(r'\[delay:\d+\]', '', clean)
    clean = re.sub(r'\[item:\d+\]', '', clean)
    clean = re.sub(r'\[name:\d+\]', '', clean)
    clean = re.sub(r'\[num:\d+\]', '', clean)
    clean = clean.replace('♣', '').replace('♦', '')
    return clean.strip()


# ============================================================
# Character name overrides (MUST match project conventions)
# ============================================================
CHARACTER_NAMES = {
    'エルク': '엘크',
    'リーザ': '리자',
    'シャンテ': '샨테',
    'シュウ': '슈우',
    'アーク': '아크',
    'ゴーゲン': '고겐',
    'トッシュ': '톳슈',
    'イーガ': '이가',
    'ちょこ': '쵸코',
    'ポコ': '포코',
    'グルガ': '그루가',
    'サニア': '사니아',
    'ケラック': '케락',
    'モフリー': '모프리',
    'ヘモジー': '헤모지',
    'チョンガラ': '총갈라',
    'ククル': '쿠쿠루',
    'ジーク': '지크',
    'ヂーク': '지크',
    'ヂークベック': '지크벡',
    'フウジン': '풍신',
    'ライジン': '뇌신',
    'オドン': '오돈',
    'ガルアーノ': '갈아노',
    'アンデル': '안델',
    'アルフレッド': '알프레드',
    'グロルガルデ': '그롤갈데',
    'ヤグン': '야군',
    'ガルムヘッド': '갈름헤드',
    'ダニー': '대니',
    'ジンバ': '진바',
}

# Town name overrides
TOWN_NAMES = {
    'プロディアス': '프로디아스',
    'インディゴス': '인디고스',
    'パレンシア': '파렌시아',
    'ロマリア': '로마리아',
    'クレニア': '크레니아',
    'ラムール': '라무르',
    'アルディア': '알디아',
    'シルバーノア': '실버노아',
    'ホルン': '호른',
    'ミルマーナ': '밀마나',
    'アララトス': '아라라토스',
    'アリバーシャ': '아리바샤',
    'グレイシーヌ': '그레이시누',
    'ニーデル': '니델',
    'ムハド': '무하드',
    'モレア': '모레아',
    'アジャール': '아자르',
    'フォーレス': '포레스',
    'サルバ': '사르바',
    'グーズ': '구스',
    'ペイサス': '페이사스',
    'ルワガ': '루와가',
    'バンザ': '반자',
    'ラマダ': '라마다',
    'スメリア': '스메리아',
    'ダウンタウン': '다운타운',
    'ピラミッド': '피라미드',
    'ブラキア': '브라키아',
    'アミーグ': '아미그',
    'バルバラード': '바르바라드',
    'ピュルカ': '퓨르카',
    'トウヴィル': '투빌',  # ○ィル → ヴィル
    'ニエン': '니엔',
    'ヒエン': '히엔',
}

# ============================================================
# Known garbled suffix patterns for location names
# ============================================================
GARBLED_SUFFIXES = {
    '固視': '여관',          # 宿屋
    '西悩': '주점',          # 酒場
    '捷導': '가도',          # 街道
    '着係罪': '연구소',       # 研究所
    '興敢殺': '연구소',       # 研究所 (different garbled form)
    '興敢腰': '연구실',       # 研究室
    '逃業腰': '실험실',       # 実験室
    '鍵皇腰': '감시실',       # 監視室
    '月悩': '술집',          # 月屋/酒場 variant
    '池視': '광장',          # 広場 likely
    '特威': '마을',          # 町
    '居己': '항구',          # 港
    '赦魂': '광산',          # 鉱山
    '辞周': '성내',          # 城内
    '辞拐': '성문',          # 城門
    '辞涙': '성벽',          # 城壁
    '辞': '성',             # 城
    '粗': '섬',             # 島
    '千一': '동굴',          # 洞窟 or similar
    'ショップ': '상점',
    'ギルド': '길드',
    'タワー': '타워',
    'トンネル': '터널',
    '滑': '숲',             # 森
    '虎': '마을',           # 村
    '威': '집',             # 家
    '何': '산',             # 山
    '悩': '옥',             # 屋
    '刀': '방',             # 部屋→方?  room
    '帰': '관',             # 館
    '腰': '실',             # 室
    '動': '원',             # 園
    '素': '궁',             # 宮
    '構腰': '본부',          # 本部
    '区周': '구역',          # 区域
    '殻地': '갑판',          # 甲板
    '算窮': '감옥',          # 監獄
    '窮度月': '해방지구',     # 解放地区
    '窮質地': '해안기지',     # 海岸基地
    '引官': '항구',          # 港口
    '引説悪消': '비행선',     # 飛行船
    '築同': '건조',          # 建造
    '捷衰辞': '가도성',      # 街道城
    '國奪': '유적',          # 遺跡
}

# ============================================================
# Known garbled terms (from BEAM overlay kanji substitution)
# ============================================================
GARBLED_TERMS = {
    # Monster name components with garbled kanji
    '歓効の天汎': '기사의 망령',    # 騎士の亡霊
    '立鬼術': '파계승',           # 破戒僧
    '細業混': '암법사',           # 闇法師
    '告典工': '수험자',           # 修験者 (告=上→修)
    '動援工': '광대',             # 道化師
    '虹の動援工': '어둠의 광대',   # 闇の道化師
    '○ァンパイアバット': '뱀파이어배트',  # ヴァンパイアバット
    '難取ヘモジー': '야생 헤모지',  # 野生ヘモジー
    '灰脂ヘモジー': '양식 헤모지',  # 養殖ヘモジー
    '更械': '사신',               # 死神
    '棄創': '강도',               # 強盗
    'リ○ァイアサン': '리바이어선',  # リヴァイアサン
    'アジッドスライム': '애시드슬라임',  # variant spelling
    '○ァニッシュ': '배니쉬',        # ヴァニッシュ
    'ラ○ィッシュ': '래비쉬',       # ラヴィッシュ (ラ○ィッシュ)
    'スーパーノ○ァ': '슈퍼노바',   # スーパーノヴァ
    '波巧': '몬지',               # 紋次
    'ロマリア絵': '로마리아왕',     # ロマリア王
    '虎潮': '마인',               # 魔人 → 村人 (but contextual)

    # Skill names with garbled kanji
    '全の土潮': '흙의 마인',       # 土の魔人
    '跳の土潮': '얼음의 마인',     # 氷の魔人
    '風の土潮': '바람의 마인',     # 風の魔人
    '殊なる土潮': '성스러운 마인',  # 聖なる魔人
    '更の土潮': '죽음의 마인',     # 死の魔人
    '号為': '자폭',               # 自爆
    'チョンガラの為共': '총갈라의 폭격',  # チョンガラの爆撃
    '館径いラッパ': '기합랩퍼',     # 気合いラッパ
    '軍鋼吟章隅': '광사자북',       # 荒獅子太鼓
    '怪立護': '도파참',            # 刀破斬
    '古丹珀為護': '벚꽃뇌폭참',    # 桜花雷爆斬
    '識捷護': '진공참',            # 真空斬
    '滝骨恐': '주박검',            # 呪縛剣
    '憎会護': '호영참',            # 虎影斬
    '液示典': '귀심법',            # 鬼心法
    '伐臆恐': '용아검',            # 竜牙剣
    '波硬護り': '몬지참',          # 紋次斬り
    '住風凶砦': '선풍격축',        # 旋風激蹴
    '上土靴臣': '퇴마광탄',        # 退魔光弾
    '泣四番立': '멸장열파',        # 滅掌烈破
    '八吐為': '유성폭',            # 流星爆
    '液械八会立': '귀신류영파',     # 鬼神流影破
    'ラマダ識況': '라마다진권',     # ラマダ真拳
    '滝骨況': '주박권',            # 呪縛拳
    '坑銀為臣': '시한폭탄',        # 時限爆弾
    '爆れ共ち': '난사',            # 乱れ撃ち
    'ヘモジー援': '헤모지화',       # ヘモジー化
    '丹撃車共': '꽃가루공격',       # 花粉攻撃
    '済奉車共': '주위공격',        # 周囲攻撃
    '関尽': '흡혈',               # 吸血
    '世煙其': '초음파',            # 超音波
    '荷互車共': '확산공격',        # 拡散攻撃
    '自り告ろし': '내려치기',       # 振り下ろし
    '為版跡飲恐': '폭렬수리검',    # 爆裂手裏剣
    '明僧げ': '머리던지기',        # 頭投げ
    '念将り': '바닥만들기',        # 床造り
    '係けない念将り': '대단한바닥만들기',  # すごい床造り (using 係けない=すごい garble)
    '寸べる': '조사',             # 調べる
    '亭下': '변신',               # 変身
    '創む': '훔치기',             # 盗む
    '驚靴従': '괴광선',           # 怪光線
    '集の斬章隅': '전쟁의 소북',    # 戦の小太鼓
    '安賞洗のオカリナ': '이다천의 오카리나',  # 韋駄天のオカリナ
    '日しの植劇': '치유의 수금',    # 癒しの竪琴
    'しあわせ靴従': '행복광선',     # しあわせ光線
    '積下の錯': '분신술',          # 分身の術
    '冠易の温慎': '황천의 계단',    # 黄泉の階段
    'モラル議脅': '모럴붕괴',       # モラル崩壊
    '場払艦故': '대량학살',        # 大量虐殺  → garbled but confirmed
    '繰座第須': '특수능력',        # 特殊能力
    '署中': '장비',               # 装備
    'やり晴し': '다시하기',        # やり直し
    'やり晴す': '다시한다',        # やり直す
    'やり晴さない': '다시하지않는다',  # やり直さない
    '低べかえ': '정렬',           # 並べかえ
    '贈重': '이름',               # 名前
    '偵れる': '헤어지기',          # 別れる
    '偵れない': '헤어지지않기',     # 別れない
    'ステータス以飼': '상태이상',    # ステータス異常
    '華耐メッセージ': '확인메시지',  # 確認メッセージ
    '熊奥煙': '효과음',           # 効果音
    '煙刑': '음성',               # 音声
    'オプション裁話': '옵션종료',    # オプション終了
    '少い': '빠름',               # 速い
    '追精': '보통',               # 普通
    '辛い': '느림',               # 遅い
    '職針': '종류',               # 種類
    '逮慎': '가격',               # 値段
    '知系': '번호',               # 番号
    '車共須': '공격력',            # 攻撃力
    '塗薬須': '방어력',           # 防御力
    '土須': '마력',               # 魔力
    '挑志然': '민첩도',            # 敏捷度

    # Weapon/equipment type labels (garbled from SCPS kanji)
    '恐': '검',                   # 剣
    '越': '도끼',                  # 斧
    '震恐': '단검',               # 短剣
    '偽': '창',                   # 槍
    '電': '봉',                   # 棒
    '聖': '지팡이',               # 杖
    '殿': '채찍',                 # 鞭
    '作': '총',                   # 銃
    '匠壮たり': '몸통박치기',       # 体当たり
    '果とばし': '얼굴던지기',       # 顔とばし
    '改': '낫',                   # 鎌
    '回再': '염주',               # 数珠
    '作2': '총2',                 # 銃2
    '明': '머리',                 # 頭
    '下匠': '몸',                 # 身体
    '介あて': '어깨보호대',        # 肩あて

    # Status labels
    '僧': '투',                   # 投
    '今': '수',                   # 受
    '断': '반',                   # 反
    '伊': '이',                   # 移
    '背': '점',                   # 跳
    '毒': '독',                   # 毒 (this one is same!)
    '靴': '광',                   # 光
    '虹': '암',                   # 闇
    '蹴破': '전용',               # 専用

    # System messages
    '繰座第須はありません': '특수능력이 없습니다',
    '繰座第須は沈哀です': '특수능력은 불명입니다',
    '署中丘第アイテム毒し': '장비가능 아이템 없음',
    '討尖非': '미등록',           # 未登録
    'L2ボタンに尖非されました': 'L2버튼에 등록되었습니다',
    'R2ボタンに尖非されました': 'R2버튼에 등록되었습니다',
    'アイテムを公った': '아이템을 사용했다',
    'はじめから': '처음부터',

    # Memory card messages
    'メモリーカードが件されていませんが[opt]ゲームをつづけますか？': '메모리카드가 없지만[opt]게임을 계속합니까?',
    'メモリーカードをセットしてください': '메모리카드를 넣어주세요',
    'どちらのカードをつかいますか？': '어느 카드를 사용합니까?',
    'メモリーカードが札髪援されていませんがフォーマットしますか？': '메모리카드가 초기화되지 않았습니다. 포맷합니까?',
    'メモリーカードがいっぱいですがゲームをつづけますか？': '메모리카드가 가득찼습니다만 게임을 계속합니까?',
    'いらないファイルをけすか、べつのカードをセットしてください': '필요없는 파일을 지우거나 다른 카드를 넣어주세요',
    'メモリーカードをチェックしています': '메모리카드를 체크중입니다',
    'メモリーカードをフォーマット衰です': '메모리카드를 포맷중입니다',
    'データをセーブしています': '데이터를 저장중입니다',
    'データをロードしています': '데이터를 불러오는중',
    'ゲームが裁話していません': '게임이 끝나지 않았습니다',
    'アーク1データへんかん': '아크1 데이터변환',
    'やめる': '그만두기',
    'このアイテムは公えません': '이 아이템은 사용할수없습니다',
    'このアイテムは贈重を亭えられません': '이 아이템은 이름을 바꿀수없습니다',
    'このアイテムはすてられません': '이 아이템은 버릴수없습니다',
    '贈重を亭紅しました': '이름을 변경했습니다',
    '贈重を曲に殴しました': '이름을 원래대로 돌렸습니다',
    '充てのキャラが署中できないアイテムです': '모든 캐릭터가 장비할수없는 아이템입니다',
    'このアイテムは署中できません': '이 아이템은 장비할수없습니다',
    '署中できない杖嚙巨善です': '장비할수없는 무기계통입니다',
    'キャラクターの紹写に断しています': '캐릭터의 속성에 반합니다',
    '葬じ職針のアイテムは署中できません': '같은 종류의 아이템은 장비할수없습니다',

    # Smithy/shop messages
    'このアイテムはもっていません': '이 아이템을 갖고있지 않습니다',
    'アイテムがたりないので径社できません': '아이템이 부족해서 합성할수없습니다',
    'アイテムがたりません': '아이템이 부족합니다',
    'すでに獣ばれています': '이미 선택되었습니다',
    '径社されるアイテムを亭紅しました': '합성될 아이템을 변경했습니다',

    # Status abbreviations
    '車': '공',                   # 攻(撃力)
    '塗': '방',                   # 防(御力)
    '土': '마',                   # 魔(力)
    '土[opt]須': '마[opt]력',     # 魔[opt]力

    # Element/type labels
    '地': '지',
    '水': '수',
    '火': '화',
    '風': '풍',

    # Skill names (garbled kanji)
    '風珀立': '풍뢰파',           # 風雷破
    '洗の原き': '하늘의 심판',     # 天の裁き

    # Location/Scene specific terms
    '濃中': '미사용',             # 未使用 (unused)
    '禁折': '엔딩',              # エンディング→ending
    '告水動': '식물원',           # 植物園
    '達木の滑': '카지노의 숲',    # gambling forest?
    '達悩': '관광지',             # 観光地 approx
    '場型装': '뒤편',             # 裏側
    '赦魂': '광산',              # 鉱山
    '事い威': '검은집',           # 黒い家
    '命し月悩': '숨겨진 술집',     # 隠し酒屋
    '痺地飲': '전투장',           # 戦地場 or similar
    '可らずの何': '닫힌 산',       # 閉ざすの山
    '母鎖の帰': '봉인의 관',      # 封印の館
    '毒潮の帰': '독의 관',        # 毒の館
    '械の素': '숲의 궁',          # 森の宮
    '性被の威': '정령의 집',       # 精霊の家
    '水の械像': '물의 숲',        # 水の森
    '言起腰': '조종실',           # 操縦室
    '言集腰': '작전실',           # 作戦室
    '言集社首': '완전승리',        # 完全勝利

    # Location names with garbled kanji (remaining 114)
    '着係罪皮活腰': '연구소활동실',    # 研究所?活動室
    '着係罪君井': '연구소병원',        # 研究所病院
    '合専乙視': '격투장',             # 格闘場
    'ガルアーノの悩豪': '갈아노의 저택',  # ガルアーノの屋敷
    '酬題興敢腰': '제국연구실',        # 帝国研究室
    '着係罪)ガイスト,': '연구소(가이스트)',  # 研究所(ガイスト)
    'ウィルの池視': '윌의 광장',       # ウィルの広場
    'ヒエン審き視': '히엔정박장',      # ヒエン着き場
    'ユドの虎': '유도의 마을',         # ユドの村
    '虎潮の威': '마인의 집',           # 魔人の家
    '○ィルマー興敢殺': '빌마연구소',   # ヴィルマー研究所
    '骸宗捷導': '해골가도',           # 骸骨街道
    '興敢腰': '연구실',              # 研究室
    '何の鍵皇斬悩': '산의 감시소',     # 山の監視小屋
    'グーズ[opt]Fバトル': '구스[opt]F배틀',
    'ホルンのつり単': '호른의 낚시터',   # ホルンのつり場
    '着係罪誕澄視': '연구소중계소',     # 研究所中継所
    '事い威告水動': '검은집식물원',     # 黒い家植物園
    '事い威鍵皇腰': '검은집감시실',     # 黒い家監視室
    '事い威逃業腰': '검은집실험실',     # 黒い家実験室
    '事い威国奪': '검은집유적',        # 黒い家遺跡
    'キメラ興敢殺逃業腰': '키메라연구소실험실',  # キメラ研究所実験室
    '逃業腰': '실험실',              # 実験室
    '着係罪過宝区': '연구소갑판',       # 研究所甲板
    'パレンシアを協微す売': '파렌시아를 찾아서',  # パレンシアを探す旅
    '地告[opt]区周': '지하[opt]구역',   # 地下[opt]区域
    '地告エレベーター周': '지하엘리베이터구역',  # 地下エレベーター区域
    'バイオ興敢殺周': '바이오연구소구역',  # バイオ研究所区域
    '地告比': '지하문',               # 地下門
    'パレンシア地告[opt]動': '파렌시아지하[opt]원',  # パレンシア地下[opt]園
    'トウ○ィルの官拐': '투빌의 항구',   # トウヴィルの港
    'トウ○ィル': '투빌',              # トウヴィル
    'ククルの械像': '쿠쿠루의 숲',      # ククルの森
    'ホルンの虎': '호른의 마을',        # ホルンの村
    'ホルンの特威': '호른의 마을집',     # ホルンの町家? → 호른의 마을
    '化の悔視': '화의 신전',           # 火の神殿
    '千一場殊装': '동굴내부',          # 洞窟内部
    'クレニアの滑': '크레니아의 숲',     # クレニアの森
    'クレニアの西悩': '크레니아의 주점',  # クレニアの酒場
    'クレニアの固視': '크레니아의 여관',  # クレニアの宿屋
    'クレニア総換視注え腰': '크레니아전투장대기실',  # クレニア闘技場控え室
    '申盤の池視': '신전의 광장',        # 神殿の広場
    'クズ先の滑ギルド': '고철의숲길드',  # クズ鉄の森ギルド
    'クズ先の滑': '고철의숲',           # クズ鉄の森
    'クズ先の滑西悩': '고철의숲주점',    # クズ鉄の森酒場
    'クズ先の滑ショップ': '고철의숲상점',  # クズ鉄の森ショップ
    'クズ先の滑固視': '고철의숲여관',    # クズ鉄の森宿屋
    'ロマリア[opt]先固視アジト': '로마리아[opt]철여관아지트',  # ロマリア[opt]鉄宿屋アジト
    'ロマリア[opt]先固視アジト言集腰': '로마리아[opt]철여관아지트작전실',
    'ザルバドの刀': '자르바드의 방',     # ザルバドの部屋
    'ヤグン算窮の月悩': '야군감옥의 술집',  # ヤグン監獄の月屋
    'ニエンの何、範虐馬級': '니엔의 산, 학살돌입',  # ニエンの山、虐殺突入
    'ニエンの何': '니엔의 산',           # ニエンの山
    '範虐側月趣薬腰': '학살침입준비실',   # 虐殺侵入準備室
    '範虐氷誕頃シーン': '학살발각시씬',   # 虐殺発覚時シーン
    '丸場範虐': '마을학살',              # 村場虐殺
    '引説悪消': '비행선',               # 飛行船
    '引説悪消堅告[opt]': '비행선최상[opt]',  # 飛行船最上[opt]
    '引説悪消過宝区': '비행선갑판',       # 飛行船甲板
    '西悩': '주점',                     # 酒場
    '固視': '여관',                     # 宿屋
    'レイガルの月悩': '레이갈의 술집',    # レイガルの月屋
    'バンザ五': '반자동굴',              # バンザ洞 (五=garbled 洞)
    'バンザ五成獅': '반자동굴내부',       # バンザ洞内部
    'サリュ承のキャンプ': '사류사의 캠프',  # サリュ族のキャンプ
    'サリュ承傷性の威': '사류사족장의 집',  # サリュ族長の家
    'とらわれ夫[opt]': '포로[opt]',       # とらわれ人[opt] (captured person)
    '夫[opt]運の月悩': '부[opt]운의 술집',  # 人[opt]運の月屋
    '感騎、跳の素抱り聞': '동쪽, 얼음의궁입구',  # 東、氷の宮入り口
    '銅騎、跳の素抱り聞': '서쪽, 얼음의궁입구',  # 西、氷の宮入り口
    '感騎、跳の素側月': '동쪽, 얼음의궁침입',   # 東、氷の宮侵入
    '銅騎、跳の素側月': '서쪽, 얼음의궁침입',   # 西、氷の宮侵入
    'キメラ興敢殺鍵皇腰': '키메라연구소감시실',  # キメラ研究所監視室
    '地告動': '지하원',                  # 地下園
    'ロマリア化地告': '로마리아성지하',    # ロマリア城地下
    'ロマリア地告切聞': '로마리아지하출구',  # ロマリア地下出口
    '清英したロマリア辞周': '격파한로마리아성내',  # 撃破したロマリア城内
    'サリュ承の虎周': '사류사의 마을구역',  # サリュ族の村周
    'ラマダ千': '라마다동굴',             # ラマダ洞 (千=garbled 洞)
    '場術借の月悩': '도술사의 술집',       # 道術者の月屋
    'トヨーケの何': '토요케의 산',         # トヨーケの山
    'アララトス[opt]偉周ダンジョン': '아라라토스[opt]유적던전',  # アララトス[opt]遺跡ダンジョン
    'アゼンダ景地': '아젠다고지',          # アゼンダ高地
    '先クズ審き視': '고철쓰레기장',        # 鉄クズ置き場
    'グレイシーヌ湿様帰': '그레이시누사원관',  # グレイシーヌ寺院館
    '引説悪消': '비행선',                # 飛行船 (duplicate)
    '跳の素': '얼음의 궁',               # 氷の宮
    'ロマリア化': '로마리아성',            # ロマリア城
    'ロマリア地告': '로마리아지하',         # ロマリア地下
    'ピュルカの虎': '퓨르카의 마을',        # ピュルカの村
    'マザークレアの帰': '마더클레어의 관',   # マザークレアの館

    # Area/Map/Battle
    '偉周': '유적',              # 遺跡
    '成獅': '내부',              # 内部
    '側月': '침입',              # 侵入
    '堅獅温': '최하층',           # 最下層
    '堅札': '처음',              # 最初
    '堅告': '최상',              # 最上
    '過宝区': '갑판',            # 甲板
    '集総': '전투',              # 戦闘
    '集肩': '전선',              # 前線
    '琥惜': '참가',              # 参加
    '衛吟': '전투',              # 戦闘
    '径社': '합성',              # 経験→合成
    '獅捷': '진입',              # 進入
    '議脅': '붕괴',              # 崩壊
    '清英': '격파',              # 撃破
    '層共': '전투',              # 戦闘
    '誕澄視': '중계소',          # 中継所
    '冗違透': '보석상',           # 宝石店
    '冗違': '보석',              # 宝石
    '総換視': '전투장',           # 戦換所→闘技場
    '注え腰': '대기실',          # 控え室
    '食従': '발사',              # 발사
    '先': '철',                  # 鉄
    '継犬の偉周': '고대의 유적',  # 古代の遺跡
    '急知': '번호',              # 番号 (variant)
    '申[opt]悩': '길드',         # ギルド garbled

    # Movie/scene descriptions
    '抱聞': '입장',              # 入場
    '抱り聞': '입구',            # 入り口
    '馬級': '돌입',              # 突入
    '鉛械勝': '비행선',          # 飛行船
    '勝獅捷': '도착진입',        # 到着進入
    '鉛械勝獅捷': '비행선진입',   # 飛行船進入
    '捷導タワーに疾抱': '가도타워에 도착',  # 街道タワーに到着
    '疾抱': '도착',              # 到着
    '事い威獅捷': '검은집진입',    # 黒い家進入
    '範虐食従': '학살발사',       # 虐殺発射
    '千一議脅': '동굴붕괴',       # 洞窟崩壊
    '械の素議脅': '숲의궁붕괴',    # 森の宮崩壊
    '引説悪消馬級': '비행선돌입',  # 飛行船突入
    '引説悪消議脅': '비행선붕괴',  # 飛行船崩壊
    '感銅騎の素議脅': '동서얼음의궁붕괴',  # 東西氷の宮崩壊
    '[opt]獅': '[opt]진입',       # [opt]進入
    '範虐': '학살',              # 虐殺
    '化': '성',                  # 城 (garbled)

    # Debug/editor labels
    'ステージ': '스테이지',
    'サウンド': '사운드',
    'アイテム': '아이템',
    'レジスタ': '레지스터',
    'OBJ知系': 'OBJ번호',
    'アニメ': '애니메',
    '伊草': '이동',              # 移動
    '荷昨': '확대',              # 拡大
    '弟戦': '회전',              # 回転
    'ジョブレディ': '잡레디',
    'ジョブ疾係': '잡대기',       # ジョブ待機
    'ジョブコンプ': '잡컴프',
    'ウォッチ': '워치',
    'リスタート': '리스타트',

    # Area map labels
    'エリアマップ': '에리어맵',
    'ワールドマップ': '월드맵',
    'ラストバトル': '라스트배틀',
    'ラストバトル内': '라스트배틀내',

    # Battle type labels
    'フリーバトル': '프리배틀',
    'エンディング': '엔딩',
    'オープニング': '오프닝',
    'ゲーム': '게임',
    'ピラミッド': '피라미드',
    'キメラ': '키메라',
    'レジスタンスアジト': '레지스탕스아지트',
    'カタパルトデッキ': '카타펄트데크',
    'バイオ': '바이오',

    # Compound location garbled parts
    'ロマリア築同興敢殺': '로마리아건조연구소',  # ロマリア建造研究所
    '協の刀': '탐색의 방',             # 探の部屋 (探索の間?)
    '運の刀': '안쪽의 방',             # 奥の部屋
    '堅獅温運の刀': '최하층안쪽의 방',   # 最下層奥の部屋
    '側月立脅': '침입작전',             # 侵入作戦
    '軍らされ': '가둬진',              # 閉じ込められ (imprisoned)
    '清英した': '격파한',              # 撃破した
    'パレンシアタワー堅獅温': '파렌시아타워최하층',
    'パレンシアタワー堅獅温運の刀': '파렌시아타워최하층안쪽의방',
    'ロマリア辞[opt][opt]協の刀': '로마리아성[opt][opt]탐색의방',
    'ロマリア辞[opt]運の刀': '로마리아성[opt]안쪽의방',
    'ロマリア辞[opt]絵の刀': '로마리아성[opt]왕의방',
    'シルバーノア側月立脅': '실버노아침입작전',
    '算窮の刀': '감옥의 방',            # 監獄の部屋
    '算窮の刀立脅': '감옥의방작전',      # 監獄の部屋作戦
    '清英したロマリア辞周': '격파한로마리아성내',

    # Full entries with ＠ markers (scene markers)
    'ロマリア[opt]先固視アジト＠軍らされ♦': '로마리아[opt]철여관아지트@가둬진♦',
    'シルバーノア側月立脅＠ロマリア辞♦': '실버노아침입작전@로마리아성♦',
    '算窮の刀＠捷衰辞♦': '감옥의방@가도성♦',
    '算窮の刀立脅＠捷衰辞♦': '감옥의방작전@가도성♦',
    'ロマリア辞[opt]絵の刀＠捷衰辞♦': '로마리아성[opt]왕의방@가도성♦',
    'ニーデル総換視＠注え腰♦': '니델전투장@대기실♦',
    'ニーデル総換視＠リング♦': '니델전투장@링♦',
    'アルディア抽＠エリアマップ♦': '알디아동@에리어맵♦',
    'アルディア太＠エリアマップ♦': '알디아서@에리어맵♦',
    'ヤゴス粗＠エリアマップ♦': '야고스섬@에리어맵♦',
    'クレニア粗＠エリアマップ♦': '크레니아섬@에리어맵♦',
    'シルバーノア築同殻地': '실버노아건조갑판',  # シルバーノア建造甲板
    '地告': '지하',               # 地下 (garbled)
    'パレンシアタワー地告': '파렌시아타워지하',

    # Misc
    '♣': '♣',
    'LV': 'LV',
    'HP': 'HP',
    'MP': 'MP',
    '？？？？？？？？？？': '??????????',
    'BGM': 'BGM',
    '？': '?',
    'S': 'S',
    'G': 'G',
    '＋': '+',
    '－': '-',
    '1': '1',
    '3': '3',
    '／': '/',

    # Single kana/character labels
    'あ': 'あ',
    'い': 'い',
    'え': 'え',
    'く': 'く',
    'た': 'た',
    'み': 'み',
    'ぶ': 'ぶ',
    'ギ': 'ギ',
    '[opt]知': '[opt]번호',      # [opt]番号
}


# ============================================================
# Build SCPS cross-reference mapping
# ============================================================
def build_scps_mapping():
    """Build JP text → KO text mapping from SCPS decoded + translated files."""
    jp_to_ko = {}

    if not os.path.exists(SCPS_DECODED_PATH) or not os.path.exists(SCPS_KO_PATH):
        print("WARNING: SCPS files not found, skipping cross-reference",
              file=sys.stderr)
        return jp_to_ko

    # Read decoded SCPS entries
    scps_decoded = {}  # offset -> text
    with open(SCPS_DECODED_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            m = LINE_RE.match(line.rstrip())
            if m:
                offset = m.group(1)
                text = m.group(3)
                scps_decoded[offset] = text

    # Read translated SCPS entries
    scps_ko = {}  # offset -> text
    with open(SCPS_KO_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            m = LINE_RE.match(line.rstrip())
            if m:
                offset = m.group(1)
                text = m.group(3)
                scps_ko[offset] = text

    # Build mapping: SCPS JP text → SCPS KO text
    for offset, jp_text in scps_decoded.items():
        if offset in scps_ko:
            ko_text = scps_ko[offset]
            clean_jp = strip_control_codes(jp_text)
            if clean_jp and clean_jp not in jp_to_ko:
                jp_to_ko[clean_jp] = ko_text
            # Also store the full text
            if jp_text not in jp_to_ko:
                jp_to_ko[jp_text] = ko_text

    print(f"  SCPS JP->KO mappings: {len(jp_to_ko)}", file=sys.stderr)
    return jp_to_ko


def parse_entries(filepath):
    """Parse a decoded/translated file and return dict of offset -> (size, text)."""
    entries = {}
    if not os.path.exists(filepath):
        return entries
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            m = LINE_RE.match(line.rstrip())
            if m:
                offset = int(m.group(1), 16)
                size = int(m.group(2))
                text = m.group(3)
                entries[offset] = (size, text)
    return entries


def translate_location_name(text):
    """Try to translate a location name using town name + suffix patterns."""
    # Try each town name as prefix
    for jp_town, ko_town in sorted(TOWN_NAMES.items(), key=lambda x: -len(x[0])):
        if text.startswith(jp_town):
            suffix = text[len(jp_town):]
            if not suffix:
                return ko_town

            # Try known suffixes
            for jp_suffix, ko_suffix in sorted(GARBLED_SUFFIXES.items(),
                                                key=lambda x: -len(x[0])):
                if suffix == jp_suffix:
                    return ko_town + ko_suffix
                if suffix.startswith(jp_suffix):
                    remaining = suffix[len(jp_suffix):]
                    # Try to translate remaining part
                    remaining_ko = GARBLED_TERMS.get(remaining, remaining)
                    return ko_town + ko_suffix + remaining_ko

            # If suffix is pure katakana, check overrides first then transliterate
            if is_pure_katakana(suffix):
                if suffix in GARBLED_TERMS:
                    return ko_town + GARBLED_TERMS[suffix]
                return ko_town + transliterate_katakana(suffix)

            # Check if suffix is in garbled terms
            if suffix in GARBLED_TERMS:
                return ko_town + GARBLED_TERMS[suffix]

            # For unknown suffix, just append the raw suffix
            # (will be handled by other strategies later)
            return None

    return None


def translate_movie_name(text):
    """Translate movie label entries like ムービーN + description."""
    m = re.match(r'^ムービー(\d+)(.*)', text)
    if m:
        num = m.group(1)
        desc = m.group(2)

        # Try to translate description piece by piece
        ko_desc = GARBLED_TERMS.get(desc)
        if ko_desc is None:
            # Try location name translation
            ko_desc = translate_location_name(desc)
        if ko_desc is None:
            # Try translating segments
            ko_desc = translate_text_segments(desc)
        if ko_desc is None:
            ko_desc = desc
        return f'무비{num}{ko_desc}'
    return None


def translate_text_segments(text):
    """Try to translate text by splitting into known segments."""
    if not text:
        return text

    # First check if the whole text is in GARBLED_TERMS
    if text in GARBLED_TERMS:
        return GARBLED_TERMS[text]

    # Split into segments of katakana vs non-katakana
    segments = re.findall(r'[ア-ヺー]+|[^ア-ヺー]+', text)
    if len(segments) <= 1:
        return None

    translated_segs = []
    for seg in segments:
        if seg in GARBLED_TERMS:
            translated_segs.append(GARBLED_TERMS[seg])
        elif seg in GARBLED_SUFFIXES:
            translated_segs.append(GARBLED_SUFFIXES[seg])
        elif seg in TOWN_NAMES:
            translated_segs.append(TOWN_NAMES[seg])
        elif seg in CHARACTER_NAMES:
            translated_segs.append(CHARACTER_NAMES[seg])
        elif is_pure_katakana(seg):
            translated_segs.append(transliterate_katakana(seg))
        elif seg == 'の':
            translated_segs.append('의 ')
        elif seg == 'に':
            translated_segs.append('에 ')
        elif seg in ('、', ','):
            translated_segs.append(', ')
        else:
            translated_segs.append(seg)

    return ''.join(translated_segs)


def translate_choko_name(text):
    """Translate ちょこのX entries."""
    m = re.match(r'^ちょこの(.+)', text)
    if m:
        suffix = m.group(1)
        ko_suffix = GARBLED_TERMS.get(suffix)
        if ko_suffix:
            return f'쵸코의 {ko_suffix}'
        # Try suffix patterns
        for jp_s, ko_s in GARBLED_SUFFIXES.items():
            if suffix == jp_s:
                return f'쵸코의 {ko_s}'
        # For katakana, check SCPS first then transliterate
        if is_pure_katakana(suffix):
            # Check GARBLED_TERMS first (has overrides for known words)
            if suffix in GARBLED_TERMS:
                return f'쵸코의 {GARBLED_TERMS[suffix]}'
            return f'쵸코의 {transliterate_katakana(suffix)}'
    return None


def translate_area_map_label(text):
    """Translate エリアマップ labels like `Town＠エリアマップ♦`."""
    m = re.match(r'^(.+)＠エリアマップ♦$', text)
    if m:
        area = m.group(1)
        # Try town names
        for jp_town, ko_town in sorted(TOWN_NAMES.items(),
                                        key=lambda x: -len(x[0])):
            if area.startswith(jp_town):
                suffix = area[len(jp_town):]
                if not suffix:
                    return f'{ko_town}@에리어맵♦'
                ko_suffix = GARBLED_TERMS.get(suffix,
                            GARBLED_SUFFIXES.get(suffix, suffix))
                return f'{ko_town}{ko_suffix}@에리어맵♦'

        # Try garbled terms
        if area in GARBLED_TERMS:
            return f'{GARBLED_TERMS[area]}@에리어맵♦'

        # Check for Aldia variants
        if 'アルディア' in area:
            suffix = area.replace('アルディア', '')
            ko_suffix = GARBLED_TERMS.get(suffix, suffix)
            return f'알디아{ko_suffix}@에리어맵♦'

        # Try to transliterate if katakana
        clean = strip_control_codes(area)
        if is_pure_katakana(clean):
            return f'{transliterate_katakana(clean)}@에리어맵♦'
    return None


def translate_free_battle(text):
    """Translate free battle labels like TownフリーバトルN."""
    m = re.match(r'^(.+)[opt]*フリーバトル(\d*)$', text)
    if not m:
        m = re.match(r'^(.+)\[opt\]フリーバトル(\d*)$', text)
    if m:
        area = m.group(1)
        num = m.group(2)
        ko_area = None
        for jp_town, ko_town in sorted(TOWN_NAMES.items(),
                                        key=lambda x: -len(x[0])):
            if area == jp_town or area.startswith(jp_town):
                suffix = area[len(jp_town):]
                ko_suffix = GARBLED_TERMS.get(suffix, suffix) if suffix else ''
                ko_area = ko_town + ko_suffix
                break
        if ko_area is None:
            ko_area = GARBLED_TERMS.get(area, area)
        return f'{ko_area} 프리배틀{num}'
    return None


def translate_compound_location(text):
    """Handle compound location names with garbled segments."""
    # Handle patterns with ＠ (scene markers)
    if '＠' in text:
        parts = text.split('＠', 1)
        main_part = parts[0]
        scene_part = parts[1] if len(parts) > 1 else ''

        ko_main = translate_text(main_part, {})
        if ko_main is None:
            ko_main = main_part

        ko_scene = ''
        if scene_part:
            # Remove trailing ♦
            scene_clean = scene_part.rstrip('♦')
            ko_scene = translate_text(scene_clean, {})
            if ko_scene is None:
                ko_scene = scene_clean
            ko_scene = '@' + ko_scene + '♦'

        return ko_main + ko_scene

    return None


def translate_text(text, scps_mapping):
    """Try all translation strategies for a single text entry.

    Returns Korean translation string or None if unable to translate.
    """
    # 1. Check garbled terms dictionary first (exact match)
    if text in GARBLED_TERMS:
        return GARBLED_TERMS[text]

    # 2. Check character names
    if text in CHARACTER_NAMES:
        return CHARACTER_NAMES[text]

    # 3. Check SCPS cross-reference (exact match on full text)
    if text in scps_mapping:
        return scps_mapping[text]

    # 4. Clean text and try SCPS match
    clean = strip_control_codes(text)
    if clean and clean in scps_mapping:
        return scps_mapping[clean]

    # 5. Check if pure katakana → transliterate
    if clean and is_pure_katakana(clean):
        # Check character name overrides first
        if clean in CHARACTER_NAMES:
            return CHARACTER_NAMES[clean]
        return transliterate_katakana(clean)

    # 6. Try location name patterns
    loc = translate_location_name(text)
    if loc:
        return loc

    # 7. Try movie name patterns
    movie = translate_movie_name(text)
    if movie:
        return movie

    # 8. Try choko name patterns
    choko = translate_choko_name(text)
    if choko:
        return choko

    # 9. Try area map labels
    area = translate_area_map_label(text)
    if area:
        return area

    # 10. Try free battle labels
    fb = translate_free_battle(text)
    if fb:
        return fb

    # 11. Try compound locations with ＠
    if '＠' in text:
        comp = translate_compound_location(text)
        if comp:
            return comp

    # 12. Try partial translation: known prefix + garbled suffix
    # Check for character name + garbled suffix
    for jp_name, ko_name in sorted(CHARACTER_NAMES.items(),
                                    key=lambda x: -len(x[0])):
        if text.startswith(jp_name):
            suffix = text[len(jp_name):]
            if suffix in GARBLED_TERMS:
                return ko_name + GARBLED_TERMS[suffix]
            if suffix in GARBLED_SUFFIXES:
                return ko_name + GARBLED_SUFFIXES[suffix]
            if suffix.startswith('の'):
                after_no = suffix[1:]
                if after_no in GARBLED_TERMS:
                    return ko_name + '의 ' + GARBLED_TERMS[after_no]
                if after_no in GARBLED_SUFFIXES:
                    return ko_name + '의 ' + GARBLED_SUFFIXES[after_no]
                if is_pure_katakana(after_no):
                    return ko_name + '의 ' + transliterate_katakana(after_no)

    # 13. Try compound location handler
    comp = translate_compound_location(text)
    if comp:
        return comp

    # 14. Try segment-based translation
    seg_result = translate_text_segments(text)
    if seg_result:
        return seg_result

    # 15. For entries that are mixed kana/kanji, try piece-by-piece
    # Split into segments of katakana vs non-katakana
    # This handles things like ガルアーノの構腰 → 갈아노의 본부
    segments = re.findall(r'[ア-ヺー]+|[^ア-ヺー]+', text)
    if len(segments) > 1:
        translated_segs = []
        all_translated = True
        for seg in segments:
            if is_pure_katakana(seg):
                # Check overrides first
                if seg in CHARACTER_NAMES:
                    translated_segs.append(CHARACTER_NAMES[seg])
                elif seg in TOWN_NAMES:
                    translated_segs.append(TOWN_NAMES[seg])
                else:
                    translated_segs.append(transliterate_katakana(seg))
            elif seg in GARBLED_TERMS:
                translated_segs.append(GARBLED_TERMS[seg])
            elif seg == 'の':
                translated_segs.append('의 ')
            elif seg == 'に':
                translated_segs.append('에 ')
            elif seg == 'を':
                translated_segs.append('을 ')
            elif seg == 'が':
                translated_segs.append('가 ')
            elif seg == 'は':
                translated_segs.append('는 ')
            elif seg == 'で':
                translated_segs.append('에서 ')
            elif seg in GARBLED_SUFFIXES:
                translated_segs.append(GARBLED_SUFFIXES[seg])
            else:
                # Can't translate this segment
                translated_segs.append(seg)
                all_translated = False

        if all_translated or len([s for s in segments
                                   if not is_pure_katakana(s)
                                   and s not in GARBLED_TERMS
                                   and s not in GARBLED_SUFFIXES
                                   and s not in ('の', 'に', 'を', 'が', 'は', 'で')
                                   ]) == 0:
            return ''.join(translated_segs)

    return None


def main():
    print("=== BEAM.DAT Missing Entries Translator ===", file=sys.stderr)

    # 1. Build SCPS cross-reference
    print("Building SCPS cross-reference...", file=sys.stderr)
    scps_mapping = build_scps_mapping()

    # 2. Read decoded and translated entries
    print("Reading BEAM.DAT files...", file=sys.stderr)
    decoded = parse_entries(DECODED_PATH)
    translated = parse_entries(TRANSLATED_PATH)

    print(f"  Decoded entries: {len(decoded)}", file=sys.stderr)
    print(f"  Translated entries: {len(translated)}", file=sys.stderr)

    # 3. Find missing entries
    missing = {}
    for offset, (size, text) in sorted(decoded.items()):
        if offset not in translated:
            missing[offset] = (size, text)

    print(f"  Missing entries: {len(missing)}", file=sys.stderr)

    # 4. Translate each missing entry
    new_entries = []  # (offset, size, korean_text)
    untranslated = []

    for offset, (size, text) in sorted(missing.items()):
        ko = translate_text(text, scps_mapping)
        if ko is not None:
            new_entries.append((offset, size, ko))
        else:
            untranslated.append((offset, size, text))

    print(f"\n=== Results ===", file=sys.stderr)
    print(f"  Translated: {len(new_entries)}", file=sys.stderr)
    print(f"  Untranslated: {len(untranslated)}", file=sys.stderr)

    if untranslated:
        print(f"\n--- Untranslated entries ({len(untranslated)}) ---",
              file=sys.stderr)
        for offset, size, text in untranslated:
            print(f"  0x{offset:08X} [{size:4d}] {text}", file=sys.stderr)

    # 5. Output new entries to stdout
    for offset, size, ko_text in new_entries:
        print(f"  0x{offset:08X} [{size:4d}] {ko_text}")

    print(f"\n# Total new entries: {len(new_entries)}", file=sys.stderr)

    return new_entries, untranslated


if __name__ == '__main__':
    main()
