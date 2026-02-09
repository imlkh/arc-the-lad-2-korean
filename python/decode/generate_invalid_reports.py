#!/usr/bin/env python3
"""Generate invalid entry reports for all decoded STG files."""

import re
import os
import unicodedata

BASE = '/Users/kyounghun/WorkSpace/ps1_game_translation/Arc_The_Lad2/atl2_korean_translation'
DECODED_DIR = os.path.join(BASE, 'output/decoded/stg')
OUTPUT_DIR = os.path.join(BASE, 'output/decoded/stg')

# Regex to parse dialogue lines (with [script:XX XX])
DIALOGUE_RE = re.compile(
    r'^  (0x[0-9A-Fa-f]+) \[(0x[0-9A-Fa-f]+)\] \[script:([0-9A-Fa-f]+ [0-9A-Fa-f]+)\](.*)'
)

# Regex for dialogue lines WITHOUT [script:XX XX]
DIALOGUE_NOSCRIPT_RE = re.compile(
    r'^  (0x[0-9A-Fa-f]+) \[(0x[0-9A-Fa-f]+)\] (?!\[script:)(.*)'
)

CONTROL_CODE_RE = re.compile(
    r'\[(?:br|opt|cursor|box:\w+|box:close|delay:[0-9A-Fa-f]+|'
    r'FF:[0-9A-Fa-f ]+|num:[0-9A-Fa-f]+|name:[0-9A-Fa-f]+|'
    r'\?[0-9A-Fa-f]+)\]'
)

# Debug keywords
DEBUG_KEYWORDS = [
    'デバック', 'バグレポート', '修正しました', '感想をください',
    '感想などもどんどん', 'debug', 'DEBUG',
]

# MIPS opcode signature characters
MIPS_CHARS = set('ギデゲッグゼノ水煙')
# Extended set for density check — chars that rarely form real Japanese words
# Excludes ジ/メ (too common in アジト, ゴメン, レジスタンス, etc.)
MIPS_DENSITY_CHARS = set('デギグダズヌ水')
# Kanji that appear from MIPS byte decoding (not real game kanji)
MIPS_KANJI = set('煙水地')
PARTIAL_HIGH_RISK_BYTES = {'80', 'F5', 'F0', 'FF'}

# Hiragana and katakana ranges
def is_hiragana(c):
    return '\u3040' <= c <= '\u309f'

def is_katakana(c):
    return '\u30a0' <= c <= '\u30ff'

def is_kana(c):
    return is_hiragana(c) or is_katakana(c)

def is_kanji(c):
    return '\u4e00' <= c <= '\u9fff'

def strip_control_codes(text):
    """Remove control codes to get plain text."""
    return CONTROL_CODE_RE.sub('', text).strip()

def is_garbage(text, plain):
    """Detect garbage / MIPS opcode patterns. Returns reason string or None."""
    if not plain:
        return None

    # Pattern 1: もあ + char + デ/ゲ/ギ (MIPS XX 01 YY 8C/80 pattern)
    if re.search(r'もあ.{0,3}[デゲギ]', plain):
        return "MIPS opcode pattern (もあXデ/ゲ/ギ)"

    # Pattern 2: 煙煙 pattern
    if '煙煙' in plain:
        return "MIPS opcode pattern (煙煙)"

    # Pattern 3: もあ煙 pattern
    if 'もあ煙' in plain:
        return "MIPS opcode pattern (もあ煙)"

    # Pattern 4: Pure MIPS chars (ギ/デ/ッ/水/グ etc.) 3+ chars
    if len(plain) >= 3 and all(c in MIPS_CHARS for c in plain):
        return "MIPS opcode pattern (pure opcode chars)"

    # Pattern 5: ぺデ prefix with short text
    if plain.startswith('ぺデ') and len(plain) <= 8:
        return "MIPS opcode pattern (ぺデ prefix)"

    # Pattern 6: Repeating same 1-2 char pattern 6+ times
    # Exempt ・ (middle dot) — silence/pause dialogue is common in RPGs
    if len(plain) >= 8:
        m = re.match(r'^(.{1,2})\1{5,}$', plain)
        if m and m.group(1) != '・':
            return f"Repeating pattern ({m.group(1)} x{len(plain)//len(m.group(1))})"

    # Pattern 7: 地+hiragana prefix (VM address pattern)
    if re.match(r'^地[あうえいお]', plain) and len(plain) >= 5:
        # Check if it has scattered あ characters (opcode fingerprint)
        a_count = plain[2:].count('あ')
        kanji_count = sum(1 for c in plain if is_kanji(c))
        if a_count >= 1 and kanji_count <= 1:
            return "MIPS opcode pattern (地+kana address)"

    # Pattern 8: ニ alternating with random kana
    if re.match(r'ニ.{1,3}ニ.{1,3}ニ', plain):
        return "MIPS opcode pattern (ニ-alternating)"

    # Pattern 9: Short text with high MIPS char density (>25% of chars)
    if len(plain) >= 3:
        degi_count = sum(1 for c in plain if c in MIPS_DENSITY_CHARS)
        if degi_count >= 2 and degi_count / len(plain) >= 0.25:
            # Also check: mostly kana with no meaning
            kanji_count = sum(1 for c in plain if is_kanji(c))
            real_kanji = kanji_count - sum(1 for c in plain if c in MIPS_KANJI)
            if real_kanji <= 0:
                # Check for actual game text patterns -
                # real text has particles, verb endings, etc.
                has_grammar = bool(re.search(
                    r'(ます|です|ない|する|した|ている|てる|こと|もの|だろう|'
                    r'かな|のは|には|では|ので|って|けど|から|まで|ても|'
                    r'なら|だな|だよ|だぜ|わよ|わね|のよ|かし|'
                    r'モグ|ダメ|'  # katakana words with MIPS density chars
                    r'ー|ァ{2}|ゥ{2}|ォ{2})',  # long vowels / onomatopoeia
                    plain
                ))
                if not has_grammar:
                    return "MIPS opcode pattern (high デ/ギ density)"

    # Pattern 10: Random hiragana string with no grammar (12+ chars, stricter)
    if len(plain) >= 12 and all(is_hiragana(c) for c in plain):
        has_grammar = bool(re.search(
            r'(ます|です|ない|する|した|ている|てる|こと|もの|だろう|'
            r'かな|のは|には|では|ので|って|けど|から|まで|ても|'
            r'なら|だな|だよ|だぜ|よう|れる|られ|せる|させ|ける|'
            r'やめ|くれ|はい|いい|ああ|おお|うう|しい|かった|たな|'
            r'たよ|たぜ|たわ|なあ|なの|んだ|のだ|けた|った|のか|'
            r'てな|だか|ほう|さん|ちゃん|ょう|しょう|ましょう|'
            r'なんだ|だけど|みたい|そうだ|ような|らしい|ている|'
            r'でしょう|ください|いただ|ありが|すみま|ごめん|'
            # Archaic/dialect patterns (old characters, regional speech)
            r'やっぱ|かもしれ|みんな|おぬし|じゃの|もどる|もどっ|'
            r'きっと|そのうち|あたる|'
            r'を[かきくけこさしすせそたちつてとなにぬねのはひふへほ])',
            plain
        ))
        if not has_grammar:
            # Check for onomatopoeia (repeated halves like ぴょこぴょこぴょこぴょこ)
            if len(plain) % 2 == 0:
                half = len(plain) // 2
                if plain[:half] == plain[half:]:
                    return None  # Onomatopoeia, not garbage
            return "Random hiragana without grammar"

    # Pattern 11: Mixed random kana + isolated uppercase ASCII
    # Exclude: G (gold unit), ON/OFF, HP/MP, common game abbreviations
    # Exclude: game rank/level patterns (レベルD, ランクA, etc.)
    if len(plain) >= 5:
        # Remove known valid ASCII usage
        check_plain = re.sub(r'\d+G', '', plain)  # Gold amounts
        check_plain = re.sub(r'(ON|OFF|HP|MP|SP|EX|LV|No)', '', check_plain)
        # Remove rank/level letters (e.g., レベルD → remove D)
        # Also remove standalone rank letters near punctuation (C、A in "レベルD、…C、…A")
        has_rank = bool(re.search(r'(レベル|ランク|クラス|タイプ|グレード)', check_plain))
        check_plain = re.sub(r'(レベル|ランク|クラス|タイプ|グレード)[A-Z]',
                             lambda m: m.group(1), check_plain)
        if has_rank:
            check_plain = re.sub(r'(?<=[、。…])[A-Z](?=[、。…]|$)', '', check_plain)
        ascii_upper = sum(1 for c in check_plain if c.isupper() and c.isascii())
        kana_count = sum(1 for c in plain if is_kana(c))
        if ascii_upper >= 2 and kana_count >= 3:
            # No kanji and has isolated uppercase (at least 2 to reduce false positives)
            kanji_count = sum(1 for c in plain if is_kanji(c))
            if kanji_count == 0:
                has_grammar = bool(re.search(
                    r'(ます|です|ない|する|した|ている|こと|もの|だろう|'
                    r'って|けど|から|まで|なら|だな|だよ|だぜ|わね|のよ|'
                    r'オーバー|モンスター|ハンター|マフィア|ギルド|'
                    r'かね|だね|なの|んだ|けど|のか)',
                    plain
                ))
                if not has_grammar and ascii_upper / len(plain) > 0.1:
                    return "Random kana with isolated ASCII"

    # Pattern 12: Very short katakana-only with MIPS-like pattern
    if len(plain) <= 5 and len(plain) >= 3:
        if all(is_katakana(c) for c in plain):
            # Check if it's a recognizable word
            known_short_kata = {
                'シゼニ', 'グゼノ', 'サデリ',  # Known MIPS patterns
            }
            if plain in known_short_kata or (
                sum(1 for c in plain if c in MIPS_CHARS) >= len(plain) * 0.5
            ):
                return "MIPS opcode pattern (short katakana)"

    # Pattern 13: 術・ prefix mixed with garbage
    if plain.startswith('術・') and any(c in MIPS_CHARS for c in plain[2:]):
        if re.search(r'[あぐ].{0,2}[関際].{0,2}[あギ]', plain):
            return "MIPS opcode pattern (術・ mixed)"

    # Pattern 14: Ends with もあ (MIPS opcode terminator 0x01=あ)
    if plain.endswith('もあ') and len(plain) <= 8:
        kanji_count = sum(1 for c in plain if is_kanji(c))
        if kanji_count == 0:
            return "MIPS opcode pattern (もあ suffix)"

    # Pattern 15: Short text (<=5 chars) with digits mixed into kana
    if len(plain) <= 5 and len(plain) >= 2:
        has_digit = any(c.isdigit() for c in plain)
        has_kana = any(is_kana(c) for c in plain)
        has_kanji = any(is_kanji(c) for c in plain)
        if has_digit and has_kana and not has_kanji:
            return "MIPS opcode pattern (digit+kana mix)"

    # Pattern 16: Non-dialogue symbols (＊, ♠) in short text
    if ('＊' in plain or '♠' in plain) and len(plain) <= 5:
        return "MIPS opcode pattern (non-dialogue symbol)"

    # Pattern 17: MIPS address register sequence (0x24 XX decoded as ジ/メ + めあ)
    # Matches the specific byte pattern where めあ (0x01) appears 2+ times
    # alongside ジ or メ — a signature of MIPS LW/SW instruction decoding.
    # Safe: ジ/メ in normal Japanese words (アジト, ゴメン, etc.) never co-occur with めあ.
    if plain.count('めあ') >= 2 and any(c in 'ジメ' for c in plain):
        return "MIPS opcode pattern (めあ+ジ/メ sequence)"

    # Pattern 19: Starts with small kana (ぉ/ゅ/ょ) — unusual word start
    if len(plain) <= 12 and plain and plain[0] in 'ぉゅょ':
        kanji_count = sum(1 for c in plain if is_kanji(c))
        if kanji_count == 0:
            return "MIPS opcode pattern (small kana start)"

    # Pattern 20: Starts with fullwidth period 。 (non-dialogue data)
    if plain.startswith('。') and len(plain) <= 5:
        return "MIPS opcode pattern (。prefix)"

    # Pattern 21: 水 + pure kana without grammar — MIPS opcode with 水 (0x90)
    if plain == '水あ':
        return "MIPS opcode pattern (水あ ADDIU)"
    if plain.startswith('水') and 5 <= len(plain) <= 12:
        rest = plain[1:]
        has_other_kanji = any(is_kanji(c) for c in rest)
        all_kana = all(is_kana(c) or c == 'ー' for c in rest)
        if not has_other_kanji and all_kana:
            has_grammar = bool(re.search(
                r'(ます|です|ない|する|した|ている|てる|こと|もの|だろう|'
                r'って|けど|から|まで|なら|んだ|のか|のは|には|ので|'
                r'の[がをにはへも])',
                rest))
            if not has_grammar:
                return "MIPS opcode pattern (水+kana)"

    # Pattern 22: Single kanji + hiragana + MIPS marker (3 chars)
    # Covers kanji+さ+ギ and kanji+hiragana+uppercase (火さI, 地おI)
    if (len(plain) == 3 and is_kanji(plain[0])
            and is_hiragana(plain[1])):
        if plain[2] == 'ギ' or (plain[2].isupper() and plain[2].isascii()):
            return "MIPS opcode pattern (kanji+hira+register)"

    # Pattern 23: Long text (>30 chars) with 2-char pair repeating 20+ times
    if len(plain) > 30:
        sample_positions = list(range(min(10, len(plain) - 1)))
        tail_start = max(10, len(plain) - 11)
        sample_positions.extend(range(tail_start, len(plain) - 1))
        seen_pairs = set()
        for i in sample_positions:
            pair = plain[i:i + 2]
            if pair in seen_pairs or pair[0] == pair[1]:
                continue
            seen_pairs.add(pair)
            if any(c in '、。！？ー…っッ' for c in pair):
                continue
            count = sum(
                1 for j in range(len(plain) - 1)
                if plain[j:j + 2] == pair)
            if count >= 20:
                return f"MIPS opcode pattern (repeating '{pair}' x{count})"

    # Pattern 24: NOR+LWL shared code block artifacts
    NOR_LWL_ARTIFACTS = {'ぱあさ', 'イしょしりあゅしう'}
    if plain in NOR_LWL_ARTIFACTS:
        return f"Pattern 24 (NOR+LWL shared block artifact): {plain}"

    # Pattern 25: Shared code block artifacts (CDT, template params, jump tables)
    SHARED_BLOCK_ARTIFACTS = {
        'げいう', 'えおよ', 'ぴおよ',
        '火そ火そボ', '火み火みボ', 'ョぬョぬボ',
        'めあ団ぷあれギ', 'やあ団C',
        'あギやしめあ団ジ', 'あギ＋おめあ団I', 'あギ管めあ団じ',
        'あギてそめあ団めあ団ぷあれギ', 'あギぷそめあ団I',
        'オゼヲ', 'あわしあ',
        'めありジマ', 'いギめありジマ',
        'オいめあげグI', 'オいめあげグJ',
        'ぴしぷしよ', 'ぷずぷずせ', 'しけしけせ',
        '渡みギC', 'カじあギじ', 'ウえあギじ', 'ヘおあギじ',
        'てギめあカゼI',
        'えあを', 'ぎしを', 'へつけ',
        # Type D: Pointer Table Entries (XxXxチ pattern)
        'ギけぇけチ', 'サそよそチ', 'のぬ、にチ', 'るこ仲チ',
        'ふし－さチ', 'サみよみチ', 'クむもむチ', 'トにがにチ',
        'ロちぺちチ', 'タのろのチ',
        # Type E: Unmasked MIPS fragments
        'めあクゼゼ', 'あギ1ぬめあ団I', '団ぷあれギ',
        # Type F: Residual MIPS artifacts
        'あわし', 'ぁぁぁ', '！こ～', '！ちい',
        'おギ！めせ', 'みぴブゥホろルげト',
        'ギシよよ', 'ぼじ', 'くきけなしたこそあこうちいて',
        'テえトくザしEた', '鉛えほさギ', 'あ団ぷあれギ',
        '地たよ', 'ュにりあぷし', 'りあ汎さギ', 'ユク水',
        'バなれちテデイちすすゾたロヌモぅ',
        'ぞビぼニぷゴミよ気グ', 'キよ逃ゲルッス', 'ゲ水ゲ',
        # Type G: Short hiragana fragments
        'ずもよ', 'がゆせ', 'りちよ', 'てにい', 'せばい', 'げどを',
        'ねけを', 'がなせ',
    }
    if plain in SHARED_BLOCK_ARTIFACTS:
        return f"Shared code block artifact: {plain}"

    # Pattern 26: XxXxY pointer table pattern (5 chars, repeated pair + terminator)
    POINTER_TERMINATORS = {'ボ', 'せ'}
    if (len(plain) == 5
            and plain[0:2] == plain[2:4]
            and plain[4] in POINTER_TERMINATORS):
        return f"Pointer table pattern ({plain[0:2]}+{plain[4]})"

    # Pattern 27: Trailing uppercase ASCII after kana/kanji
    # Exempt rank patterns: レベルD, ランクA, クラスS, etc.
    if (len(plain) >= 3
            and plain[-1].isupper() and plain[-1].isascii()
            and any(is_kana(c) or is_kanji(c) for c in plain[:-1])):
        if plain[-2].isupper() and plain[-2].isascii():
            pass  # Consecutive uppercase (HP, MP) — not garbage
        elif re.search(r'(レベル|ランク|クラス|タイプ|グレード)[A-Z]$', plain):
            pass  # Rank pattern — not garbage
        else:
            return f"MIPS register trailing ({plain[-1]})"

    # Pattern 28: [opt] + mixed ASCII+kana (padding gibberish)
    # Strip ALL bracket tags to avoid false positives from [script:XX], [item:XX]
    plain_all_stripped = re.sub(r'\[[^\]]*?\]', '', text).strip()
    if '[opt]' in text and len(plain_all_stripped) >= 8:
        has_lower = any(c.islower() and c.isascii() for c in plain_all_stripped)
        has_kana_p28 = any(is_kana(c) for c in plain_all_stripped)
        if has_lower and has_kana_p28:
            return "Padding mixed-script gibberish"

    # Pattern 29 (REMOVED): Short hiragana fragment — too many false positives
    # Pattern 30 (REMOVED): Medium repeat threshold — too many false positives
    # Short garbage fragments are now caught by the SHARED_BLOCK_ARTIFACTS blocklist.

    return None


def is_single_char(plain):
    """Check if this is a single character fragment (not valid punctuation dialogue)."""
    if len(plain) != 1:
        return False
    # Single punctuation marks ARE valid dialogue (reactions: ？=confusion, …=silence, ！=surprise)
    valid_single = set('？！…・ー')
    if plain in valid_single:
        return False
    return True


def is_debug(text, plain):
    """Check if this is a debug/developer message."""
    for keyword in DEBUG_KEYWORDS:
        if keyword in plain or keyword in text:
            return True
    # Debug menu with FF:04 02 01 items
    if '[FF:04 02 01]' in text and ('ギルド' in text or 'debug' in text.lower() or
                                      'XA再生' in text or '分配器' in text or 'ずかん' in text):
        return True
    # Developer shop statistics messages
    if 'おみせでかいものをした' in plain:
        return True
    if 'うりものをみてた' in plain:
        return True
    if 'かじやは' in plain and 'レベルアップ' in plain:
        return True
    if 'ごいけんくださいね' in plain:
        return True
    if 'バランスについても' in plain:
        return True
    return False


def is_partial_decode(text, plain, script_tag):
    """Check if this is a partial decode (missing first char)."""
    # Script tag starting with specific high-risk bytes often indicates
    # truncated first-byte decode (observed mojibake clusters).
    script_bytes = script_tag.split()
    if (len(script_bytes) == 2 and script_bytes[0] == '00'
            and script_bytes[1] in PARTIAL_HIGH_RISK_BYTES):
        if plain and len(plain) >= 2:
            return f"Possible truncated first byte (script:00 {script_bytes[1]})"

    # Also check explicit continuation fragments independent of script bytes.
    if plain and len(plain) >= 3:
        partial_starts = [
            ('ュウ', 'シュウ'), ('ころで', 'ところで'), ('ございました', 'ありがとうございました'),
            ('ごめい', 'ごめいわく'),
        ]
        for start, full in partial_starts:
            if plain.startswith(start):
                return f"Truncated (likely {full})"

    return None


def analyze_file(filepath):
    """Analyze a decoded STG file and return categorized invalid entries."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    garbage = []      # Category 1
    single_chars = [] # Category 2
    debug_msgs = []   # Category 3
    partial = []      # Category 4
    no_script = []    # Category 5
    total_dialogues = 0
    header = lines[0].strip() if lines else ''

    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        m = DIALOGUE_RE.match(line)
        if m:
            total_dialogues += 1
            offset = m.group(1)
            speaker = m.group(2)
            script_tag = m.group(3)
            text = m.group(4)
            plain = strip_control_codes(text)

            # Check categories in priority order
            reason = is_garbage(text, plain)
            if reason:
                garbage.append((line_num, offset, speaker, script_tag, text, reason))
                continue

            if is_single_char(plain):
                single_chars.append((line_num, offset, speaker, script_tag, text))
                continue

            if is_debug(text, plain):
                debug_msgs.append((line_num, offset, speaker, script_tag, text))
                continue

            reason = is_partial_decode(text, plain, script_tag)
            if reason:
                partial.append((line_num, offset, speaker, script_tag, text, reason))
            continue

        # Check for dialogue lines without [script:XX XX]
        m = DIALOGUE_NOSCRIPT_RE.match(line)
        if m:
            total_dialogues += 1
            offset = m.group(1)
            speaker = m.group(2)
            text = m.group(3)
            no_script.append((line_num, offset, speaker, text))

    return {
        'header': header,
        'total': total_dialogues,
        'garbage': garbage,
        'single_chars': single_chars,
        'debug': debug_msgs,
        'partial': partial,
        'no_script': no_script,
    }


def write_report(stg_name, result, output_path):
    """Write an invalid entries report."""
    excluded = len(result['garbage']) + len(result['single_chars']) + len(result['debug'])
    partial_count = len(result['partial'])
    no_script_count = len(result['no_script'])

    lines = []
    lines.append(f"# {stg_name} Invalid Entries Report")
    lines.append(f"# Total dialogues: {result['total']}")
    lines.append(f"# Invalid entries excluded from translation: {excluded}")
    lines.append(f"# Partial decodes included in translation: {partial_count}")
    lines.append(f"# Missing script prefix: {no_script_count}")

    if result['garbage']:
        lines.append(f"")
        lines.append(f"## Category 1: Garbage / MIPS Opcodes ({len(result['garbage'])} entries)")
        lines.append(f"## These are misinterpreted MIPS opcodes or binary data, not actual dialogue.")
        lines.append(f"")
        for entry in result['garbage']:
            line_num, offset, speaker, script, text, reason = entry
            lines.append(f"  Line {line_num:>4}: {offset} [{speaker}] [script:{script}]{text}")
            lines.append(f"    → {reason}")

    if result['single_chars']:
        lines.append(f"")
        lines.append(f"## Category 2: Single Character Fragments ({len(result['single_chars'])} entries)")
        lines.append(f"## Decoder artifacts — single characters with no meaningful dialogue content.")
        lines.append(f"")
        for entry in result['single_chars']:
            line_num, offset, speaker, script, text = entry
            lines.append(f"  Line {line_num:>4}: {offset} [{speaker}] [script:{script}]{text}")

    if result['debug']:
        lines.append(f"")
        lines.append(f"## Category 3: Debug / Developer Messages ({len(result['debug'])} entries)")
        lines.append(f"## Left by developers for internal testing. Not meant for players.")
        lines.append(f"")
        for entry in result['debug']:
            line_num, offset, speaker, script, text = entry
            lines.append(f"  Line {line_num:>4}: {offset} [{speaker}] [script:{script}]{text}")

    if result['partial']:
        lines.append(f"")
        lines.append(f"## Category 4: Partial Decodes ({len(result['partial'])} entries)")
        lines.append(f"## These have truncated first character(s) due to decoder limitations.")
        lines.append(f"## INCLUDED in translation with the missing character(s) restored where possible.")
        lines.append(f"")
        for entry in result['partial']:
            line_num, offset, speaker, script, text, reason = entry
            lines.append(f"  Line {line_num:>4}: {offset} [{speaker}] [script:{script}]{text}")
            lines.append(f"    → {reason}")

    if result['no_script']:
        lines.append(f"")
        lines.append(f"## Category 5: Missing Script Prefix ({len(result['no_script'])} entries)")
        lines.append(f"## Dialogue lines without [script:XX XX] prefix. May need decoder fix.")
        lines.append(f"")
        for entry in result['no_script']:
            line_num, offset, speaker, text = entry
            lines.append(f"  Line {line_num:>4}: {offset} [{speaker}] {text}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return excluded, partial_count, no_script_count


def main():
    stg_files = sorted([
        f for f in os.listdir(DECODED_DIR)
        if f.endswith('_STG.txt')
    ])

    print(f"Found {len(stg_files)} decoded STG files\n")
    print(f"{'File':<16} {'Total':>6} {'Garbage':>8} {'Single':>7} {'Debug':>6} {'Partial':>8} {'NoScript':>9} {'Excluded':>9}")
    print("-" * 85)

    for fname in stg_files:
        stg_name = fname.replace('_STG.txt', '.STG')
        input_path = os.path.join(DECODED_DIR, fname)
        output_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '_invalid_report.txt'))

        result = analyze_file(input_path)
        excluded, partial_count, no_script_count = write_report(stg_name, result, output_path)

        print(f"{stg_name:<16} {result['total']:>6} {len(result['garbage']):>8} "
              f"{len(result['single_chars']):>7} {len(result['debug']):>6} "
              f"{len(result['partial']):>8} {no_script_count:>9} {excluded:>9}")

    print()
    print("Reports written to:", OUTPUT_DIR)


if __name__ == '__main__':
    main()
