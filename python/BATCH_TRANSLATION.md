# Batch Translation System for Arc the Lad 2

Translates remaining Japanese dialogue lines to Korean using small parallel batch jobs to avoid context limits.

## Overview

The full game has ~20,568 dialogue lines across 19 STG files. Some files are fully translated, others are partial. This system splits the ~12,810 remaining untranslated lines into 436 batch files of ~30 lines each, translates them via Claude Code subagents, then merges the results back.

## Files

| Script | Purpose |
|--------|---------|
| `python/translate_batch_prep.py` | Compares source vs translated, creates batch files |
| `python/translate_batch_run.py` | Prompt template and instructions for Claude Code subagents |
| `python/translate_batch_merge.py` | Merges completed batch outputs into final translation files |

## Directory Layout

```
python/stg_decoded/             # Source decoded STG files (Japanese)
translated/ko/                  # Korean translation output files
translated/ko/batches/          # Batch working directory
translated/ko/batches/manifest.json
translated/ko/batches/S100_batch_000.txt      # Source JP batch
translated/ko/batches/S100_batch_000_ko.txt   # Translated KR output
```

## Translation Status

Fully translated (no work needed):

| File | Dialogues |
|------|-----------|
| S300 | 320 |
| SC00 | 702 |
| SG00 | 1,493 |
| SH00 | 49 |
| SJ00 | 0 |

Partially translated (batches created):

| File | Translated | Remaining | Batches |
|------|-----------|-----------|---------|
| S100 | 162 | 1,005 | 34 |
| S200 | 351 | 1,406 | 47 |
| S400 | 777 | 1 | 1 |
| S500 | 525 | 1 | 1 |
| S600 | 119 | 634 | 22 |
| S700 | 933 | 1,635 | 55 |
| S800 | 267 | 664 | 23 |
| S900 | 131 | 791 | 27 |
| SA00 | 75 | 1,194 | 40 |
| SB00 | 776 | 1 | 1 |
| SD00 | 664 | 1 | 1 |
| SE00 | 143 | 1,070 | 36 |
| SF00 | 134 | 2,365 | 79 |
| SI00 | 137 | 2,042 | 69 |
| **Total** | | **12,810** | **436** |

## Usage

### Step 1: Prepare batches

```
python3 python/translate_batch_prep.py
```

Compares each source file (`python/stg_decoded/<NAME>_STG.txt`) against the existing Korean translation (`translated/ko/<NAME>_STG.txt`) by matching hex offsets. Lines whose offsets appear in the translated file are considered done. Everything after the last translated offset is split into batch files of 30 dialogue lines each.

Output:
- `translated/ko/batches/<NAME>_batch_NNN.txt` -- source Japanese lines
- `translated/ko/batches/manifest.json` -- tracks batch status

### Step 2: Translate batches

Tell Claude Code:

> Read `python/translate_batch_run.py` and execute the batch translation.

Claude Code will:
1. Read the manifest to find pending batches
2. Spawn background `general-purpose` subagents (up to 5 in parallel)
3. Each subagent reads one batch file (~30 JP dialogue lines), translates to Korean, and writes `<NAME>_batch_NNN_ko.txt`
4. Mark each batch as `"done"` in the manifest after completion

Each subagent uses ~2-3K tokens of context (30 lines + translation prompt), so it never hits context limits.

### Step 3: Merge results

```
python3 python/translate_batch_merge.py
```

Options:
- `--dry-run` -- preview what would be merged without writing

Reads the manifest, concatenates completed batch outputs in order, and appends them to the existing `translated/ko/<NAME>_STG.txt` files. Only merges contiguous completed batches from the start to preserve ordering. Reports any gaps.

### Resuming after interruption

The system is resumable. If interrupted mid-translation:
1. The manifest tracks which batches are `"pending"` vs `"done"`
2. Re-running Step 2 picks up where it left off
3. Completed `_ko.txt` files are not regenerated

## File Format

Source and translated files share the same format:

```
  0xOFFSET [0xOPCODE] [script:XX XX]Dialogue text here
  0xOFFSET [0xOPCODE] [script:XX XX][box:speech]More dialogue\nwith line break
  --- context: 0xXXXX -> 0xXXXX ---
```

- **Hex offset**: Memory address in the original binary, used as the unique key
- **Opcode**: Speaker/character identifier (e.g., `0x8005` = Elk, `0xFFFE` = NPC)
- **Script codes**: Control commands preserved as-is
- **Tags**: `[box:speech]`, `[box:close]`, `[delay:XX]`, `[opt]`, `[item:XX]` -- all preserved exactly
- **Context separators**: Mark speaker changes, copied verbatim

Translation replaces only the Japanese text portion after the last `]` bracket.

## Character Name Mappings

| Japanese | Korean | Character |
|----------|--------|-----------|
| エルク | 엘크 | Elk |
| リーザ | 리자 | Lieza |
| アーク | 아크 | Arc |
| ククル | 쿠쿠루 | Kukuru |
| シャンテ | 샨테 | Shante |
| ポコ | 포코 | Poco |
| トッシュ | 토슈 | Tosh |
| ゴーゲン | 고겐 | Gogen |
| シュウ | 슈우 | Shu |
| イーガ | 이가 | Iga |
| グルガ | 그루가 | Gruga |
| サニア | 사니아 | Sania |
| ちょこ/チョコ | 쵸코 | Choco |
| ヂークベック | 지크벡 | Diekbeck |
| ガルアーノ | 갈아노 | Galuano |
| ヤグン | 야군 | Yagun |

## Place Name Mappings

| Japanese | Korean |
|----------|--------|
| ロマリア | 로말리아 |
| アルディア | 알디아 |
| プロディアス | 프로디아스 |
| ミルマーナ | 밀마나 |
| スメリア | 스메리아 |
| グレイシーヌ | 그레이슈뉴 |
| パレンシア | 팔렌시아 |
| シルバーノア | 실버노아 |
| インディゴス | 인디고스 |
| ホルン | 호른 |
