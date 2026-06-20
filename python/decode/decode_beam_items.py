#!/usr/bin/env python3
"""Decode BEAM.DAT overlay item table and generate Korean translation entries.

BEAM.DAT contains a PS-X EXE overlay at file offset 0x209D000 with its own
item name table. This table uses FF:19 separators (vs SCPS's FF:1A).

Strategy:
- The BEAM overlay item table is structurally identical to the SCPS item table
  but with FF:19 separators instead of FF:1A, and with some SCPS compound
  entries merged or split differently.
- Items decode to the same text (katakana/romaji items match exactly; kanji
  items may decode differently due to overlay byte differences).
- We flatten both SCPS and BEAM item lists, build a JP->KO mapping from SCPS,
  then match BEAM items by text content. For garbled kanji items, we use the
  known 1:1 positional correspondence.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))

sys.path.insert(0, SCRIPT_DIR)
from decode_text import build_decode_table
from decode_scps_items import resolve_items as resolve_items_scps
from decode_scps_items import build_reverse_table

# --- Paths ---
BEAM_PATH_PRIMARY = os.path.join(PROJECT_DIR, "output", "original", "BEAM.DAT")
BEAM_PATH_FALLBACK = os.path.normpath(os.path.join(PROJECT_DIR, "..", "BEAM.DAT"))

SCPS_DECODED_PATH = os.path.join(PROJECT_DIR, "output", "decoded", "bin",
                                  "SCPS_100_26.txt")
SCPS_KO_PATH = os.path.join(PROJECT_DIR, "translated", "ko", "SCPS_100_26.txt")

# --- BEAM overlay item table region ---
ITEM_TABLE_START = 0x0216E4CC
ITEM_TABLE_END = 0x0216ECC0  # Right before character name table


def find_beam_dat():
    """Locate the BEAM.DAT file."""
    for p in [BEAM_PATH_PRIMARY, BEAM_PATH_FALLBACK]:
        if os.path.exists(p):
            return p
    print("Error: BEAM.DAT not found", file=sys.stderr)
    sys.exit(1)


def extended_char_id(high_byte, low_byte):
    return (high_byte - 0xF0) * 255 + low_byte + 239


def parse_beam_entries(data, table_start, table_end, decode_table):
    """Parse binary data into entries: list of (offset, byte_len, decoded_text)."""
    entries = []
    pos = 0
    end = table_end - table_start

    while pos < end:
        b = data[pos]
        if b == 0x00:
            pos += 1
            continue

        # Start of new entry
        entry_start = pos
        parts = []

        while pos < end and data[pos] != 0x00:
            b = data[pos]

            if b == 0xFF and pos + 3 < end:
                sub = data[pos + 1]
                p1 = data[pos + 2]
                p2 = data[pos + 3]
                parts.append(f"[FF:{sub:02X} {p1:02X} {p2:02X}]")
                pos += 4
            elif 0xF0 <= b <= 0xFE and pos + 1 < end:
                second = data[pos + 1]
                char_id = (b - 0xF0) * 255 + second + 239
                char = decode_table.get(char_id, f"[?{char_id}]")
                parts.append(char)
                pos += 2
            elif b == 0xEF:
                parts.append("[opt]")
                pos += 1
            elif 0x01 <= b <= 0xEE:
                char = decode_table.get(b, f"[?{b}]")
                parts.append(char)
                pos += 1
            else:
                parts.append(f"[{b:02X}]")
                pos += 1

        text = "".join(parts)
        byte_len = pos - entry_start
        file_offset = table_start + entry_start
        entries.append((file_offset, byte_len, text))

        # Skip null terminator
        if pos < end:
            pos += 1

    return entries


def resolve_beam_items(text, decode_table, reverse_table):
    """Resolve a BEAM entry with [FF:19 00 XX] separators into individual items."""
    sep_pattern = re.compile(r'\[FF:19 00 ([0-9A-Fa-f]{2})\]')

    def resolve_prefix(t):
        def replace_prefix(m):
            sub = int(m.group(1), 16)
            yy = int(m.group(2), 16)
            zz = int(m.group(3), 16)
            if sub == 0x19:
                return m.group(0)
            if yy >= 0xF0:
                ext_id = extended_char_id(yy, zz)
                ch = decode_table.get(ext_id, f'[?ext:{ext_id}]')
                return ch
            else:
                ch1 = decode_table.get(yy, f'[?{yy:02X}]')
                ch2 = decode_table.get(zz, f'[?{zz:02X}]')
                return ch1 + ch2
        return re.sub(r'\[FF:([0-9A-Fa-f]{2}) ([0-9A-Fa-f]{2}) ([0-9A-Fa-f]{2})\]',
                      replace_prefix, t)

    parts = sep_pattern.split(text)
    items = []
    first = resolve_prefix(parts[0])
    items.append(first)

    for i in range(1, len(parts), 2):
        xx = int(parts[i], 16)
        segment = parts[i + 1] if i + 1 < len(parts) else ""
        segment = resolve_prefix(segment)

        if xx == 0x00:
            item = segment
        elif 0x01 <= xx <= 0xEE:
            ch = decode_table.get(xx, f'[?{xx:02X}]')
            item = ch + segment
        elif 0xF0 <= xx <= 0xFE:
            if segment:
                first_char = segment[0]
                rest = segment[1:]
                low_byte = reverse_table.get(first_char)
                if low_byte is not None and low_byte <= 0xEE:
                    ext_id = extended_char_id(xx, low_byte)
                    ext_char = decode_table.get(ext_id, f'[?ext:{ext_id}]')
                    item = ext_char + rest
                else:
                    item = f'[EXT:{xx:02X}+{first_char}?]' + rest
            else:
                item = f'[EXT:{xx:02X}]'
        elif xx == 0xFF:
            if segment:
                item = segment[1:]
            else:
                item = ""
        else:
            item = f'[?{xx:02X}]' + segment

        items.append(item)

    return items


def build_scps_flat_mapping(decode_table, reverse_table):
    """Build flat list of (japanese_name, korean_name) from SCPS translation.

    Returns list of (jp_resolved, ko_name) tuples in table order.
    """
    line_re = re.compile(r'^\s+0x([0-9A-Fa-f]+)\s+\[\s*(\d+)\]\s+(.+)$')

    # Read decoded SCPS (Japanese with FF:1A codes)
    scps_entries = []  # list of (offset, items_list)
    with open(SCPS_DECODED_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if '[FF:1A' not in line:
                continue
            m = line_re.match(line.rstrip())
            if m:
                offset = m.group(1)
                text = m.group(3)
                items = resolve_items_scps(text, decode_table, reverse_table)
                items = [it.strip() for it in items if it.strip()]
                scps_entries.append((offset, items))

    # Read Korean translations (with FF:1A 00 00 separators)
    ko_entries = []
    with open(SCPS_KO_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if '[FF:1A' not in line:
                continue
            m = line_re.match(line.rstrip())
            if m:
                offset = m.group(1)
                text = m.group(3)
                items = re.split(r'\[FF:1A 00 00\]', text)
                items = [it.strip() for it in items if it.strip()]
                ko_entries.append((offset, items))

    # Build flat mapping by matching offsets
    flat_mapping = []  # (jp_name, ko_name) in order
    jp_to_ko = {}      # jp_name -> ko_name (for text-based matching)

    scps_by_offset = {off: items for off, items in scps_entries}
    ko_by_offset = {off: items for off, items in ko_entries}

    for offset in scps_by_offset:
        if offset not in ko_by_offset:
            continue
        jp_items = scps_by_offset[offset]
        ko_items = ko_by_offset[offset]

        count = min(len(jp_items), len(ko_items))
        for j in range(count):
            jp = jp_items[j].strip()
            ko = ko_items[j].strip()
            if jp and ko:
                flat_mapping.append((jp, ko))
                if jp not in jp_to_ko:
                    jp_to_ko[jp] = ko

    return flat_mapping, jp_to_ko


def has_trailing_separator(decoded_text):
    """Check if the original decoded text ends with a FF:19 separator."""
    return bool(re.search(r'\[FF:19 00 [0-9A-Fa-f]{2}\]\s*$', decoded_text))


def main():
    beam_path = find_beam_dat()
    print(f"Using BEAM.DAT: {beam_path}", file=sys.stderr)

    decode_table = build_decode_table()
    reverse_table = build_reverse_table(decode_table)

    # Step 1: Build SCPS JP->KO mapping
    print("Building SCPS item mapping...", file=sys.stderr)
    flat_mapping, jp_to_ko = build_scps_flat_mapping(decode_table, reverse_table)
    print(f"  SCPS flat items: {len(flat_mapping)}", file=sys.stderr)
    print(f"  Unique JP->KO mappings: {len(jp_to_ko)}", file=sys.stderr)

    # Step 2: Read and decode BEAM item table
    print("Reading BEAM.DAT item table...", file=sys.stderr)
    with open(beam_path, 'rb') as f:
        f.seek(ITEM_TABLE_START)
        data = f.read(ITEM_TABLE_END - ITEM_TABLE_START + 16)

    entries = parse_beam_entries(data, ITEM_TABLE_START, ITEM_TABLE_END,
                                 decode_table)
    print(f"  BEAM entries: {len(entries)}", file=sys.stderr)

    # Step 3: Flatten BEAM items
    beam_flat = []  # list of (entry_idx, item_idx, resolved_name)
    for ei, (off, blen, text) in enumerate(entries):
        if '[FF:19' in text:
            items = resolve_beam_items(text, decode_table, reverse_table)
            items_clean = [it.strip() for it in items]
            for ii, item in enumerate(items_clean):
                beam_flat.append((ei, ii, item))
        else:
            beam_flat.append((ei, 0, text.strip()))

    print(f"  BEAM flat items: {len(beam_flat)}", file=sys.stderr)

    # Step 4: Match BEAM items to Korean translations
    # Strategy: First try direct text match, then use known positional mapping
    # for garbled items.

    # Build the positional mapping by aligning the flat item lists.
    # The BEAM and SCPS item tables contain the same items in the same overall
    # order, but grouped into different compound entries.
    # We flatten both and align them.

    # Known alignment of BEAM flat items to SCPS flat items by position:
    beam_to_ko = {}  # beam_flat_idx -> korean_name

    # First pass: match by decoded text
    matched_by_text = 0
    unmatched_indices = []
    for bi, (ei, ii, name) in enumerate(beam_flat):
        if name in jp_to_ko:
            beam_to_ko[bi] = jp_to_ko[name]
            matched_by_text += 1
        else:
            unmatched_indices.append(bi)

    print(f"  Matched by text: {matched_by_text}", file=sys.stderr)
    print(f"  Unmatched: {len(unmatched_indices)}", file=sys.stderr)

    # Second pass: for unmatched items, use the known SCPS positional order
    # The BEAM item table entries correspond to SCPS in the following way:
    # BEAM compound entries E0-E18 correspond to SCPS compound entries 0-27
    # (weapons + armor + shields) but merged/split differently.
    # BEAM individual entries E19-E46 = SCPS accessory items from entries 28-29
    # BEAM E47-E54 = SCPS entries 30-35 (gems, status items, consumables)
    #
    # Build a manual positional map for the known garbled items.
    # We know the exact order from comparing resolved items above.

    # SCPS flat items are in order: items[0..191]
    # For each BEAM flat item that didn't match by text, find its SCPS
    # counterpart by looking at its position in the table.

    # The BEAM table items in sequential order correspond 1:1 to SCPS items
    # EXCEPT for a few differences in grouping. Let's build the explicit
    # mapping.

    # SCPS flat order (from resolve_items_scps output):
    # 0-3: ソード, ブレイド, エッジ, 剣
    # 4-7: スレイヤー, ウエポン, カタナ, サムライブレイド
    # 8-9: ハンドアックス, ハンマー
    # 10-12: ライトハンマー, アックス, ウォーハンマー
    # 13-15: ライトフレイル, フレイル, フレイル
    # 16-17: チェインフレイル, モーニングスター
    # 18-20: ナイフ, クリス, ナイフ
    # 21-24: ダガー, シルバーナイフ, ショートソード, カタール
    # 25-27: スピア, スピア, トライデント
    # 28-32: パルチザン, ハルバード, スピア, クラブ, ポール
    # 33-35: パワークラブ, メタルストライカー, ボーパルクラブ
    # 36-37: ワンド, ロッド
    # 38-40: スタッフ, スケールロッド, ウォースタッフ
    # 41-45: アイアンナックル, クロー, ナックル, クロー, フィスト
    # 46-50: ライトシューズ, ひざあて, シューズ, ニードルシューズ, ドラゴンブーツ
    # 51-57: ライトシンバル, サウンド, クラッシュシンバル, シンバル, ウィップ, ニードル, ドラゴンウィップ
    # 58-61: マシンガン, ニードルガン, バレット, ディメンションガン
    # 62-70: パッド, ビートアタッカー, パワーパッド, ブレイカー, ファング, ビーク, ファング, ファング, ダイノファング
    # 71-78: メタルフェイス, シャドウルック, パープルアイ, ライトシックル, サイズ, シックル, ボーパルサイズ, ブラッディムーン
    # 79-80: ブラックカード, カード
    # 81: ミラクルカード
    # 82-84: ホワイトビーズ, ロザリー, デッドリープレイ
    # 85-87: ショットガン, ドーリーショット, グレネード
    # 88-94: 布の服, 皮の服, ハードレザー, 戦闘服, ライトスーツ, スーツ, スーツ
    # 95: ローブ
    # 96-97: ローブ, マント  -> wait, 95=ローブ is part of entry25, 96-97 are entry26
    # 98-104: 皮の肩あて, ライトアーム, ショルダー, ガード, アーム, ラウンドガード, ガード
    # 105-119: accessories (SCPS entry 28)
    # 120-133: accessories (SCPS entry 29)
    # 134: 蒼い宝石
    # 135: 緑の宝石
    # 136: 紅い宝石
    # 137-144: status items (SCPS entry 33)
    # 145-161: consumables (SCPS entry 34)
    # 162-191: consumables (SCPS entry 35)

    # BEAM flat order (from resolve_beam_items output):
    # 0-3: ソード, ブレイド, エッジ, 恐(=剣)
    # 4-7: スレイヤー, ウエポン, カタナ, サムライブレイド
    # 8-12: ハンドアックス, ハンマー, ライトハンマー, アックス, ウォーハンマー
    # 13-18: ライトフレイル, フレイル, フレイル, チェインフレイル, モーニングスター, フレイル
    # 19-25: ナイフ, クリス, ナイフ, ダガー, シルバーナイフ, ショートソード, カタール
    # 26-36: スピア, スティンガー, トライデント, パルチザン, ハルバード, スピア, クラブ, ポール, ライトポール, メタルストライカー, ボーパルクラブ
    # 37-40: ワンド, ロッド, スタッフ, スケールロッド
    # 41-45: アイアンナックル, クロー, ナックル, クロー, フィスト
    # 46-50: ライトシューズ, ひざあて, シューズ, ニードルレッグ, ドラゴンブーツ
    # 51-57: ライトシンバル, サウンド, クラッシュシンバル, シンバル, ウィップ, ニードル, ドラゴンウィップ
    # 58-61: マシンガン, ニードルガン, バレット, ディメンションガン
    # 62-70: パッド, ビートアタッカー, パワーパッド, ブレイカー, ファング, ビーク, ファング, ファング, ダイノファング
    # 71-79: マスク, メタルフェイス, シャドウルック, パープルアイ, ライトシックル, サイズ, シックル, ボーパルサイズ, ブラッディムーン
    # 80-82: ブラックカード, カード, ミラクルカード
    # 83-85: ホワイトビーズ, ロザリー, デッドリープレイ
    # 86-88: ショットガン, ドーリーショット, グレネード
    # 89-94: 態の綱, 替の綱, ハードレザー, 集総綱, ライトスーツ, スーツ
    # 95-97: ローブ, ローブ, マント
    # 98-103: 替の介あて, ライトアーム, ショルダー, ガード, アーム, ラウンドガード
    # (individual items E19-E46 start here = BEAM flat indices 104-131)
    # 104: 苦乗の能費 (古代の指輪)
    # ... through to ...
    # 131: 亜いくつ (赤いくつ)
    # 132: [opt]刺り (守り - with separator)
    # ... then color gems, etc.

    # The differences are:
    # 1. BEAM has extra item 'フレイル' at flat[18] (extra entry in flails)
    # 2. BEAM has 'スティンガー' and 'ライトポール' not in SCPS compound list
    # 3. BEAM has 'ニードルレッグ' instead of 'ニードルシューズ'
    # 4. BEAM has 'マスク' extra at flat[71]
    # 5. BEAM is missing some items from SCPS to keep overall count similar

    # This tells me BEAM and SCPS are NOT exactly 1:1 - they have different
    # item lists! BEAM is a different overlay with some different items.
    # I need to match the items that DO match and provide manual translations
    # for the BEAM-only items.

    print('', file=sys.stderr)
    print('=== Unmatched BEAM items ===', file=sys.stderr)
    for bi in unmatched_indices:
        ei, ii, name = beam_flat[bi]
        print(f'  flat[{bi:3d}] E{ei:2d}.{ii:2d}: {name}', file=sys.stderr)

    # Manual translations for BEAM-only items and garbled kanji items
    MANUAL_KO = {
        # BEAM-only weapon items
        'スティンガー': '스팅어',
        'ライトポール': '라이트폴',
        'ニードルレッグ': '니들레그',
        'マスク': '마스크',
        # Garbled kanji items (same as SCPS but decoded differently in overlay)
        '恐': '검',                    # 剣 = sword
        '態の綱': '무명옷',            # 布の服 = cloth garment
        '替の綱': '가죽옷',            # 皮の服 = leather garment
        '集総綱': '전투복',            # 戦闘服 = battle suit
        '替の介あて': '가죽어깨보호대',  # 皮の肩あて = leather shoulder guard
        '苦乗の能費': '고대의 반지',      # 古代の指輪
        '任混の施': '용자의 증표',        # 勇者の証
        '砂風の寸べ': '조풍의 선율',      # 潮風の調べ
        'おし丹の度': '압화책',          # おし花の本
        'ゆかりの波支': '인연의 문장',     # ゆかりの紋章
        'おもちゃの能費': '장난감 반지',   # おもちゃの指輪
        '煙博在': '음악집',             # 音楽集
        '土須の回再': '마력의 염주',       # 魔力の数珠
        '棄須な聖': '지팡이',            # (杖→)棄須な聖 = 杖
        'ディールの臆': '디르의 송곳니',   # ディールの牙
        '地携のスコープ': '지옥의 스코프',  # 地獄のスコープ
        '絵孤の勝': '왕의 상',            # 王様の像
        'エルク蹴破': '에르크전용',        # エルク専用
        'リーザ蹴破': '리자전용',          # リーザ専用
        'シャンテ蹴破': '샹테전용',        # シャンテ専用
        'シュウ蹴破': '슈우전용',          # シュウ専用
        '吸署尻': '흑장속',              # 黒装束
        'サニア蹴破': '사니아전용',        # サニア専用
        'グルガ蹴破': '그루가전용',        # グルガ専用
        '冠育いリボン': '노란 리본',       # 黄色いリボン
        '亜いくつ': '빨간 구두',          # 赤いくつ
        '刺り': '부적',                 # 守り
        '[opt]い冗違': '푸른 보석',       # [opt]蒼い宝石
        '堂の冗違': '녹색 보석',          # 緑の宝石
        '休い冗違': '붉은 보석',          # 紅い宝石
        '買': '거울',                   # 鏡
        'ラークの波支': '라크의 문장',     # ラークの紋章
        '倉よけの能費': '독방지 반지',     # 毒よけの指輪
        'たかの勝': '매의 상',            # たかの像
        'クラ○ィスの度': '클라비스의 책',  # クラヴィスの本 (○ = garbled ヴ)
        '義所': '약초',                 # 薬草
        '弟包奥妻': '회복과일',           # 回復果物 -> garbled
        '棄須奥妻': '강력과일',           # 強力果物 -> garbled
        '取遺の鎌の逃': '생명의 나무열매',  # 生命の木の実
        '土典のりんご': '마법의 사과',      # 魔法のりんご
        '土須の易': '마력의 샘',           # 魔力の泉
        'ちからの逃': '힘의 열매',          # ちからの実
        '土須の叩': '마력의 잎',           # 魔力の葉
        'レコの所': '레코의 풀',           # レコの草
        'パロの逃': '파로의 열매',          # パロの実
        'みなぎる奥逃': '넘치는 과실',      # みなぎる果実
        '包戒の義': '부활의 약',           # 復活の薬
        '刺りの義': '수호의 약',           # 守りの薬
        '[?ext:4082]査りの義': '약화의 약', # 弱りの薬
        '為臣': '폭탄',                  # 爆弾
        '当第義': '만능약',               # 万能薬
        'やる館ゼリー': '의욕젤리',         # やる気ゼリー
        '違落け担': '석화해제침',           # 石解け針
        'ルウの義': '루우의 약',            # ルウの薬
        '堂の準い切所': '녹색 추억풀',      # 緑の想い出草
        '倉よけの逃': '독방지 열매',        # 毒よけの実
        '薙の義': '눈의 약',              # 目の薬
        '生番な担': '통렬한 침',           # 痛烈な針
        '車共直': '공격병',               # 攻撃瓶
        '示の職': '마음의 씨앗',           # 心の種
        '軌い叩': '쓴 잎',               # 苦い葉
        'すばやさ直': '민첩병',            # すばやさ瓶
        'ラドの逃': '라드의 열매',          # ラドの実
        '血れるりんご': '저린 사과',        # 痺れるりんご
        '泥の準い切所': '보라 추억풀',      # 紫の想い出草
        '独り城': '잠의 구슬',            # 眠り玉
        '倉義': '독약',                  # 毒薬
        '薙つぶしの所': '눈뭉개풀',        # 目つぶしの草
        '冠育い撃': '노란 가루',           # 黄色いこな
        '査りの城': '약화의 구슬',          # 弱りの玉
        '忌縄請け': '하룻밤절임',           # 一夜漬け
        'ジャンプ担': '점프침',            # ジャンプ針
        'レブの逃': '레브의 열매',          # レブの実
        'テムの所': '템의 풀',             # テムの草
        '吸い撃': '검은 가루',            # 黒いこな
        'さわやか所': '상쾌풀',            # さわやか草
        # Items that need special handling
        '[EF]い冗違': '푸른 보석',         # Alternative garble for 蒼い宝石
    }

    # Apply manual translations to unmatched
    manual_matched = 0
    still_unmatched = []
    for bi in unmatched_indices:
        ei, ii, name = beam_flat[bi]
        if name in MANUAL_KO:
            beam_to_ko[bi] = MANUAL_KO[name]
            manual_matched += 1
        else:
            still_unmatched.append((bi, ei, ii, name))

    print(f"  Manual matched: {manual_matched}", file=sys.stderr)
    if still_unmatched:
        print(f"  Still unmatched: {len(still_unmatched)}", file=sys.stderr)
        for bi, ei, ii, name in still_unmatched:
            print(f"    flat[{bi:3d}] E{ei:2d}.{ii:2d}: {name}", file=sys.stderr)

    # Step 5: Generate output entries
    print("", file=sys.stderr)
    print("=== Generating BEAM_DAT.txt entries ===", file=sys.stderr)

    output_lines = []
    flat_idx = 0

    for ei, (file_offset, byte_len, decoded_text) in enumerate(entries):
        if '[FF:19' in decoded_text:
            # Compound entry - reconstruct with Korean item names
            items = resolve_beam_items(decoded_text, decode_table, reverse_table)
            items_clean = [it.strip() for it in items]

            # Check if entry has trailing separator (produces empty last item)
            trailing_sep = has_trailing_separator(decoded_text)

            ko_parts = []
            for ii, item in enumerate(items_clean):
                ko = beam_to_ko.get(flat_idx, item)
                ko_parts.append(ko)
                flat_idx += 1

            # Remove trailing empty parts (produced by trailing separator)
            while ko_parts and not ko_parts[-1]:
                ko_parts.pop()

            # Join with [FF:19 00 00] separator
            ko_text = "[FF:19 00 00]".join(ko_parts)

            # Restore trailing separator if original had one
            if trailing_sep:
                ko_text += "[FF:19 00 00]"

            output_lines.append(
                f"  0x{file_offset:08X} [{byte_len:4d}] {ko_text}")
        else:
            # Single item entry
            ko = beam_to_ko.get(flat_idx, decoded_text.strip())
            flat_idx += 1
            output_lines.append(
                f"  0x{file_offset:08X} [{byte_len:4d}] {ko}")

    # Print output (to stdout for piping)
    print("# BEAM.DAT Overlay — Item/Equipment Tables "
          "(Korean translations)")
    print("# Separator: [FF:19 00 00] (BEAM overlay equivalent "
          "of SCPS [FF:1A 00 00])")
    print("")
    for line in output_lines:
        print(line)

    print(f"\n# Total: {len(output_lines)} entries, "
          f"{len(beam_flat)} items", file=sys.stderr)

    return output_lines


if __name__ == '__main__':
    main()
