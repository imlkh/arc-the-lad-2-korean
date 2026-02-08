#!/usr/bin/env python3
"""Generate invalid entry reports for all decoded STG files."""

import re
import os
import unicodedata

BASE = '/Users/kyounghun/WorkSpace/ps1_game_translation/Arc_The_Lad2/atl2_korean_translation'
DECODED_DIR = os.path.join(BASE, 'output/decoded/stg')
OUTPUT_DIR = os.path.join(BASE, 'output/decoded/stg')

# Regex to parse dialogue lines
DIALOGUE_RE = re.compile(
    r'^  (0x[0-9A-Fa-f]+) \[(0x[0-9A-Fa-f]+)\] \[script:([0-9A-Fa-f]+ [0-9A-Fa-f]+)\](.*)'
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
        if a_count >= 2:
            return "MIPS opcode pattern (地+kana address)"

    # Pattern 8: ニ alternating with random kana
    if re.match(r'ニ.{1,3}ニ.{1,3}ニ', plain):
        return "MIPS opcode pattern (ニ-alternating)"

    # Pattern 9: Short text with high デ/ギ density (>25% of chars)
    if len(plain) >= 4:
        degi_count = sum(1 for c in plain if c in 'デギ')
        if degi_count >= 2 and degi_count / len(plain) >= 0.25:
            # Also check: mostly kana with no meaning
            kanji_count = sum(1 for c in plain if is_kanji(c))
            if kanji_count == 0 or (kanji_count == 1 and '煙' in plain):
                # Check for actual game text patterns -
                # real text has particles, verb endings, etc.
                has_grammar = bool(re.search(
                    r'(ます|です|ない|する|した|ている|てる|こと|もの|だろう|'
                    r'かな|のは|には|では|ので|って|けど|から|まで|ても|'
                    r'なら|だな|だよ|だぜ|わよ|わね|のよ|かし)',
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
    if len(plain) >= 5:
        # Remove known valid ASCII usage
        check_plain = re.sub(r'\d+G', '', plain)  # Gold amounts
        check_plain = re.sub(r'(ON|OFF|HP|MP|SP|EX|LV|No)', '', check_plain)
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
    total_dialogues = 0
    header = lines[0].strip() if lines else ''

    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        m = DIALOGUE_RE.match(line)
        if not m:
            continue

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

    return {
        'header': header,
        'total': total_dialogues,
        'garbage': garbage,
        'single_chars': single_chars,
        'debug': debug_msgs,
        'partial': partial,
    }


def write_report(stg_name, result, output_path):
    """Write an invalid entries report."""
    excluded = len(result['garbage']) + len(result['single_chars']) + len(result['debug'])
    partial_count = len(result['partial'])

    lines = []
    lines.append(f"# {stg_name} Invalid Entries Report")
    lines.append(f"# Total dialogues: {result['total']}")
    lines.append(f"# Invalid entries excluded from translation: {excluded}")
    lines.append(f"# Partial decodes included in translation: {partial_count}")

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

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return excluded, partial_count


def main():
    stg_files = sorted([
        f for f in os.listdir(DECODED_DIR)
        if f.endswith('_STG.txt')
    ])

    print(f"Found {len(stg_files)} decoded STG files\n")
    print(f"{'File':<16} {'Total':>6} {'Garbage':>8} {'Single':>7} {'Debug':>6} {'Partial':>8} {'Excluded':>9}")
    print("-" * 75)

    for fname in stg_files:
        stg_name = fname.replace('_STG.txt', '.STG')
        input_path = os.path.join(DECODED_DIR, fname)
        output_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '_invalid_report.txt'))

        result = analyze_file(input_path)
        excluded, partial_count = write_report(stg_name, result, output_path)

        print(f"{stg_name:<16} {result['total']:>6} {len(result['garbage']):>8} "
              f"{len(result['single_chars']):>7} {len(result['debug']):>6} "
              f"{len(result['partial']):>8} {excluded:>9}")

    print()
    print("Reports written to:", OUTPUT_DIR)


if __name__ == '__main__':
    main()
