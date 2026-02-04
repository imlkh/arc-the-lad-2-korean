# YGUILD.BIN Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `YGUILD.BIN` |
| Size | 102,400 bytes (100.0 KB) |
| Date | Nov 7, 1996 |
| Type | PS1 MIPS executable overlay + embedded guild quest data |
| Load address | RAM `0x80026000` |
| Active data | 36,288 bytes (35.4% of file) |
| Zero padding | 65,756 bytes (64.2% of file) |
| Contains text | **Yes** -- 363 translatable text strings |

## Purpose

YGUILD.BIN is the **Hunter's Guild System Module** -- a dynamically-loaded PS1 MIPS overlay that handles the Hunter's Guild quest/job system. It manages quest listings, job briefings, reward calculations, and quest result messages. The module contains 100 quest definitions with titles, descriptions, multiple outcome messages (failure/success variants), and reward parameters.

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x00017` | 24 bytes | **Jump Table** | 6 x 4-byte RAM addresses (`0x80026Bxx`) |
| `0x00018`-`0x03947` | 14,640 bytes (14.3 KB) | **MIPS Code** | 78 functions (72 prologues, 78 JR RA returns) |
| `0x03948`-`0x03CDF` | 924 bytes | **Quest Reward Table** | 154 x 6-byte reward/difficulty records |
| `0x03CE0`-`0x03E47` | 360 bytes | **Zero Gap** | Alignment padding |
| `0x03E48`-`0x03FD7` | 400 bytes | **Pointer Table 1 (Titles)** | 100 x 4-byte table-relative offsets to quest titles |
| `0x03FD8`-`0x045FF` | 1,576 bytes | **Pointer Table 2 (Descriptions+Results)** | 394 x 4-byte table-relative offsets |
| `0x04600`-`0x047A7` | 424 bytes | **Pointer Table 3 (Late Results)** | 106 x 4-byte table-relative offsets |
| `0x047A8`-`0x08F25` | 18,302 bytes (17.9 KB) | **Quest Text Data** | 363 null-terminated text strings |
| `0x08F26`-`0x12E47` | 40,738 bytes (39.8 KB) | **Zero Padding** | Main padding region |
| `0x12E48`-`0x12F22` | 219 bytes | **Secondary Data Island** | CharID mapping table + UI configuration |
| `0x12F23`-`0x18FFF` | 24,797 bytes (24.2 KB) | **Zero Padding** | Final padding to 100 KB |

### Shannon Entropy

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | 2.96 bits/byte | Low (70.2% null bytes from padding) |
| MIPS Code | ~6.0 bits/byte | Typical for compiled MIPS code |
| Quest Text | ~5.5 bits/byte | Typical for encoded Japanese game text |

## MIPS Code Region (0x00018 - 0x03947)

### Jump Table (0x0000 - 0x0017)

Unlike SMITH.BIN's offset-based jump table, YGUILD.BIN starts with 6 RAM addresses pointing to functions within the code region:

| Index | RAM Address | File Offset | Description |
|-------|------------|-------------|-------------|
| 0 | `0x80026B30` | `0x0B30` | Guild menu handler |
| 1 | `0x80026B48` | `0x0B48` | Quest list handler |
| 2 | `0x80026B60` | `0x0B60` | Quest detail handler |
| 3 | `0x80026B78` | `0x0B78` | Quest accept handler |
| 4 | `0x80026B90` | `0x0B90` | Quest result handler |
| 5 | `0x80026BB0` | `0x0BB0` | Cleanup/exit handler |

The first function starts at offset `0x0018` (not `0x0088` as in SMITH.BIN), immediately after the jump table. This compact layout suggests a simpler module structure.

### Code Statistics

| Property | Value |
|----------|-------|
| Code size | 14,640 bytes (14.3 KB) |
| Function prologues | 72 |
| JR RA returns | 78 |
| Last JR RA | `0x03940` |
| LUI references | 151 to `0x8004xxxx`, 37 to `0x8002xxxx`, 30 to `0x8003xxxx` |

The dominant LUI target `0x8004xxxx` indicates heavy interaction with the main game executable's data structures (likely the quest state arrays and party status).

### Code Cross-References

129 of 136 LUI/ADDIU address pairs resolve to valid file offsets with base `0x80026000`, confirming the load address. Key targets include:
- `0x80029948` (file `0x03948`): Quest reward table
- `0x80029E48` (file `0x03E48`): Pointer table base (used for text lookup)
- `0x80029BA0` (file `0x03BA0`): Internal data function

## Quest Reward Table (0x03948 - 0x03CDF)

154 records of 6 bytes each, containing quest reward parameters:

### Record Format

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| +0x00 | 2 bytes | `reward` | Gold reward amount (LE uint16) |
| +0x02 | 2 bytes | `difficulty` | Difficulty rating (LE uint16) |
| +0x04 | 2 bytes | `group_id` | Quest group/location identifier (LE uint16) |

### First 100 Records (Quest Rewards)

The first 100 records correspond to the 100 guild quests, grouped by location/chapter:

| Group ID | Record Range | Quest Range | Count | Reward Range | Difficulty |
|----------|-------------|-------------|-------|-------------|------------|
| `0x000D` (13) | 0-18 | Quests 0-18 | 19 | 400-6,000 | 2-12 |
| `0x0002` (2) | 19-28 | Quests 19-28 | 10 | 800-4,000 | 2-8 |
| `0x0050` (80) | 29-38 | Quests 29-38 | 10 | 2,000-6,000 | 5-7 |
| `0x008D` (141) | 39-48 | Quests 39-48 | 10 | 2,000-4,000 | 5-8 |
| `0x0074` (116) | 49-58 | Quests 49-58 | 10 | 2,000-6,000 | 5-8 |
| `0x010C` (268) | 59-63 | Quests 59-63 | 5 | — | — |
| `0x00AA` (170) | 64-68 | Quests 64-68 | 5 | — | — |
| `0x00A0` (160) | 69-73 | Quests 69-73 | 5 | — | — |
| `0x013F` (319) | 74-78 | Quests 74-78 | 5 | — | — |
| `0x00D0` (208) | 79-83 | Quests 79-83 | 5 | — | — |
| `0x0102` (258) | 84-88 | Quests 84-88 | 5 | — | — |
| `0x00BE` (190) | 89-99 | Quests 89-99 | 11 | — | — |

### Records 100-153 (Extended Parameters)

54 additional records with alternating patterns of large and small values, likely defining bonus rewards, experience multipliers, or chapter-specific quest parameters.

## Pointer Table Structure

All three pointer tables use **offsets relative to the Pointer Table 1 base address** (`0x3E48`), identical to SDIC.BIN's approach.

### Resolution Formula

```
text_file_offset = 0x3E48 + pointer_value
```

### Pointer Table 1 — Quest Titles (0x3E48 - 0x3FD7)

100 x 4-byte LE offsets pointing to quest title strings.

| Entry | Offset | Resolved | Title |
|-------|--------|----------|-------|
| 0 | `0x0960` | `0x47A8` | インディゴス下水道調べ |
| 1 | `0x0A52` | `0x489A` | 廃墟の幽霊屋敷 |
| 2 | `0x0B4C` | `0x4994` | インディゴス宝石強盗団 |
| ... | | | |
| 99 | `0x509A` | `0x8EE2` | ギルド請負仕事その100タイトル |

### Pointer Table 2 — Descriptions + Results (0x3FD8 - 0x45FF)

394 x 4-byte LE offsets, organized in two sections:

**Section A (entries 0-99):** Quest **briefing descriptions** — detailed job postings explaining what the quest involves. Parallel to Table 1 (entry N in Table 1 is the title, entry N in Table 2a is the description).

**Section B (entries 100-393):** Quest **result messages** — 294 entries providing multiple outcome variants per quest. Each quest typically has 4 result entries:

| Sub-entry | Purpose |
|-----------|---------|
| 0 | Failure message |
| 1 | Partial success |
| 2 | Success |
| 3 | Great success (大成功) |

Many result entries share the same offset (duplicate pointers), indicating that some quests reuse the same success message across multiple outcome levels.

### Pointer Table 3 — Late Quest Results (0x4600 - 0x47A7)

106 x 4-byte LE offsets pointing to result messages for quests in the latter half of the quest list. Contains 41 unique text pointers (many duplicates for shared outcome messages).

## Quest Text Data (0x047A8 - 0x08F25)

### Overview

| Property | Value |
|----------|-------|
| Total strings | 363 |
| Region size | 18,302 bytes |
| First string | `0x047A8` |
| Last string | `0x08F0A` |
| Encoding | Standard game text (see `TEXT_ENCODING.md`) |

### Content Categories

| Category | Count | Description |
|----------|-------|-------------|
| Quest titles | ~62 | Named quest titles (e.g., "インディゴス下水道調べ") |
| Placeholder titles | ~38 | "ギルド請負仕事そのXXXタイトル" (unused quest slots) |
| Quest descriptions | ~100 | Detailed job briefings |
| Quest results | ~125 | Outcome messages (failure/success variants) |
| Placeholder results | ~38 | "ギルド請負仕事そのXXX" / "大成功メッセージ" |
| **Total** | **363** | |

Of the 100 quest slots, approximately 62 contain real quest content with unique titles, descriptions, and result messages. The remaining ~38 slots are placeholders with generic titles like "ギルド請負仕事その011タイトル" (Guild contract job #011 title), suggesting they were reserved for future content or DLC-style expansion.

### Sample Quest Data

#### Quest 0: インディゴス下水道調べ (Indigos Sewer Investigation)

| Field | Text |
|-------|------|
| **Title** | インディゴス下水道調べ |
| **Description** | 少し前から下水がつまり、大変困っている。しかし下水道にはモンスターがでるため、入ることも出来ない。そこで、腕の立つハンターにゴミをとり除いてきて欲しい。 |
| **Fail** | 下水に詰まったゴミを掃除しに行った。詰まっていたゴミは、なんとびっくりスライムの群だったが、結構強くて歯が立たなかった。 |
| **Success** | 下水をつまらせていた原因は、スライムだった。残らず始末して仕事完了。 |

#### Quest 1: 廃墟の幽霊屋敷 (Haunted House in Ruins)

| Field | Text |
|-------|------|
| **Title** | 廃墟の幽霊屋敷 |
| **Description** | 町外れに、昔おさない子供が殺されたという「幽霊屋敷」と呼ばれる家がある。好奇心おうせいな子供達が、よく屋敷の近くで遊んでいるのだが、心配なので本当に幽霊が出るのか調べて欲しい。 |
| **Fail** | 廃屋の幽霊退治を頼まれたが、どうも歯が立ちそうにないのであきらめた。 |
| **Success** | 廃屋の幽霊退治を頼まれ、それまで救われることのなかった二つの魂を成仏させることに成功。 |

#### Quest 9: 面接試験有、山賊お断り (Interview Required, Bandits Need Not Apply)

| Field | Text |
|-------|------|
| **Title** | 面接試験有、山賊お断り |
| **Description** | 仕事を頼みたいのだが、引き受けてもらうかどうかは会ってから決めたいという。依頼人はアルディア橋にいるので、「今日はいい天気だな」と言われたら、「そうでもねえよ」と答えて欲しい。 |

### All 100 Quest Titles

| # | Title | Status |
|---|-------|--------|
| 0 | インディゴス下水道調べ | Active |
| 1 | 廃墟の幽霊屋敷 | Active |
| 2 | インディゴス宝石強盗団 | Active |
| 3 | 地下から怪しげな歌声が… | Active |
| 4 | 廃屋の人形師 | Active |
| 5 | 廃墟の謎の集団 | Active |
| 6 | バーンズさんの犬捜し | Active |
| 7 | 無人の酒場で毎夜ピアノの音が… | Active |
| 8 | 続・インディゴス宝石強盗団 | Active |
| 9 | 面接試験有、山賊お断り | Active |
| 10-18 | ギルド請負仕事その011~019タイトル | Placeholder |
| 19 | インディゴウイスキー運び | Active |
| 20 | 迷子の子供捜し | Active |
| 21 | 武器ドロボウ退治 | Active |
| 22 | 空き屋敷のモンスター退治 | Active |
| 23 | 大泥棒から財産を守って欲しい | Active |
| 24 | リベンジ・オブ・ザ・女泥棒 | Active |
| 25 | モンスターを殺してください | Active |
| 26 | 私をインディゴスに連れてって | Active |
| 27 | 辻斬り御用 | Active |
| 28 | ギルド請負仕事その029タイトル | Placeholder |
| 29 | 先祖の宝捜しを手伝って！ | Active |
| 30 | 先祖の宝捜しその後 | Active |
| 31 | 父さんの仇討ちの助太刀をして | Active |
| 32-38 | ギルド請負仕事その033~039タイトル | Placeholder |
| 39 | 息子にお守りを届けておくれ | Active |
| 40 | クズ鉄の大穴の恐怖のガス | Active |
| 41 | モンスターがあふれでてくる！？ | Active |
| 42-43 | ギルド請負仕事その043~044タイトル | Placeholder |
| 44 | 鉄クズ置き場でのクズ鉄拾いの警護 | Active |
| 45 | 再生品を盗む犯人を捕まえて欲しい | Active |
| 46 | 夜な夜な来るモンスターを倒して | Active |
| 47-48 | ギルド請負仕事その048~049タイトル | Placeholder |
| 49 | 旅から帰らない息子を捜して欲しい | Active |
| 50 | いたずら息子を捕まえて欲しい | Active |
| 51 | ベリンガル笑劇場を警護して欲しい | Active |
| 52 | ホルンの村に食料を届けて欲しい | Active |
| 53-58 | ギルド請負仕事その054~059タイトル | Placeholder |
| 59 | 新メニュー用食材探し | Active |
| 60 | 家を探してます | Active |
| 61 | 愛の告白、僕に勇気を下さい！ | Active |
| 62 | ラマダ山に、モンスターが！ | Active |
| 63 | ギルド請負仕事その064タイトル | Placeholder |
| 64 | 石板調査の護衛 | Active |
| 65 | 海竜の卵返却 | Active |
| 66 | 炭坑の落盤事故の炭坑夫救出作業 | Active |
| 67-68 | ギルド請負仕事その068~069タイトル | Placeholder |
| 69 | 酒場のゴロつき退治 | Active |
| 70 | 迷子のロバ探し | Active |
| 71 | アミーグロックの羽根を探せ | Active |
| 72 | 長老館の紛失事件 | Active |
| 73 | ギルド請負仕事その074タイトル | Placeholder |
| 74 | おじいさんを捜してください | Active |
| 75 | 謎のモンスター闘技場占拠 | Active |
| 76 | 闘技場モンスター反乱 | Active |
| 77-78 | ギルド請負仕事その078~079タイトル | Placeholder |
| 79 | 指輪探し | Active |
| 80 | 迷子の少女 | Active |
| 81 | 砂漠の神隠し | Active |
| 82 | あぶない薬 | Active |
| 83 | ギルド請負仕事その084タイトル | Placeholder |
| 84 | 砂漠の盗賊団を撃退してくれ | Active |
| 85 | 続・砂漠の盗賊団 | Active |
| 86-88 | ギルド請負仕事その087~089タイトル | Placeholder |
| 89 | 線路の上の岩石取り除き作業 | Active |
| 90 | 落とした鉱石の収拾 | Active |
| 91 | 病気を治す草を取ってくる | Active |
| 92 | ふとっちょのために肉を取ってくる | Active |
| 93 | トロッコ占領のモンスター退治 | Active |
| 94 | モンスターの卵を取ってくる | Active |
| 95 | 子供達がモンスターに！ | Active |
| 96-99 | ギルド請負仕事その097~100タイトル | Placeholder |

**Active quests: ~62 / 100 slots used**

## Secondary Data Island (0x12E48 - 0x12F22)

219 bytes of initialized data separated from the main content by a 40 KB zero gap.

### Structure

| Sub-Offset | Size | Content |
|------------|------|---------|
| `0x12E48`-`0x12E8F` | 72 bytes | **CharID mapping table** — sequential 16-bit character IDs (`0x02EF`-`0x0308`) for number/symbol rendering in the guild UI |
| `0x12E90`-`0x12F22` | 147 bytes | **UI configuration records** — 28-byte parameter blocks with display layout values (position, size, item count) |

The CharID mapping table contains character indices for rendering guild-specific UI elements (quest numbers, rank symbols, reward amounts) using the font in `COMM.IMG`.

## Text Encoding

Text strings use the standard game encoding (see `TEXT_ENCODING.md`):

| Byte Range | Encoding | CharID Range |
|------------|----------|--------------|
| `0x00` | Null terminator | -- |
| `0x01`-`0xEE` | Single byte | 1-238 |
| `0xEF` | Choice option prefix | -- |
| `0xF0 XX`-`0xF5 XX` | Two bytes | 239-1768 |
| `0xFF sub p1 p2` | Control code | -- |

The `[opt]` (0xEF) prefix appears in some quest description strings, marking interactive choice points where the player can accept or decline a quest.

## Comparison with Other Overlay Modules

| Property | SDIC.BIN | SMITH.BIN | YGUILD.BIN |
|----------|----------|-----------|------------|
| Load address | `0x80026000` | `0x80028000` | `0x80026000` |
| File size | 102,400 bytes | 102,400 bytes | 102,400 bytes |
| Code size | 16.0 KB (21 funcs) | 24.6 KB (108 funcs) | 14.3 KB (78 funcs) |
| Text entries | 555 | 628 | 363 |
| Text size | 13.8 KB | 38.0 KB | 17.9 KB |
| Active data | 38.9% | 68.0% | 35.4% |
| Pointer base | Table-relative | Direct file offsets | Table-relative |
| Content | Profiles, bestiary | Item descriptions | Guild quests |

Note: YGUILD.BIN and SDIC.BIN share the same load address (`0x80026000`), confirming they are **mutually exclusive overlays** — only one can be loaded at a time. The game swaps them in and out of the same RAM region as needed.

## Relevance to Korean Translation

### Text that needs translation

YGUILD.BIN contains **363 translatable text entries** totaling ~18,302 raw bytes:

1. **~62 quest titles**: Named quest titles displayed in the guild job listing
2. **~100 quest descriptions**: Detailed briefings explaining each quest's objectives
3. **~125 quest result messages**: Outcome text for failure, partial success, and full success
4. **~38 placeholder labels**: Generic strings for unused quest slots ("ギルド請負仕事そのXXXタイトル") — these can be left as-is or translated

### Modification approach

1. **Replace text strings**: Translate each null-terminated string in the `0x047A8`-`0x08F25` region
2. **Update pointer tables**: All three pointer tables (`0x3E48`, `0x3FD8`, `0x4600`) use table-relative offsets. If string lengths change, recalculate all pointers using: `new_pointer = new_text_offset - 0x3E48`
3. **Preserve reward table**: The quest reward table at `0x3948` is purely numerical and does not need translation
4. **Update CharID mapping**: The secondary data island at `0x12E48` contains character IDs for UI number rendering — these may need updating if the Korean font mapping changes character positions

### Available space

The text region currently uses 18,302 bytes with 40,738 bytes of zero padding following it. This provides ample room for text expansion. Korean translations of the quest text should fit comfortably within the available space.

### Dependencies

| File | Role |
|------|------|
| `YGUILD.BIN` | Guild quest code + text (this file) |
| `SDIC.BIN` | Text rendering functions (loaded separately, same RAM address) |
| `COMM.IMG` | Font texture (character glyphs) |
| `SCPS_100.26` | Main executable: quest state management, party data |
| `S*.STG` | Stage data (quest-related stages/maps) |
