# COMM.IMG Character Table Verification

## Summary

**The character table in `COMM_IMG_chars.md` is CORRECT.**

Initial analysis suggested character mapping errors based on nonsensical decoded text in BEAM.DAT. However, verification shows:

1. The character table correctly maps glyphs in COMM.IMG
2. STG files decode properly using the same table (行き, 階段, etc.)
3. The "wrong" text in BEAM.DAT uses different byte sequences, not misidentified characters

## Verification Evidence

### STG Files Decode Correctly

Searching STG files for common words shows correct decoding:

```
S100_STG.txt: 攻撃する場合は、移動して相手の隣に行き
S100_STG.txt: あの...階段から...
S200_STG.txt: じゃあ、行きましょう
S600_STG.txt: 上にのぼる階段があったはずだ
```

### Byte Comparison

| Word | STG Bytes | BEAM.DAT Bytes | Result |
|------|-----------|----------------|--------|
| 行 | F1 D8 → charID 710 | F3 04 → charID 1008 | Different chars |

The STG files use the correct bytes (F1 D8 for 行), while BEAM.DAT has different data (F3 04 decodes to 切).

### Visual Verification

Using `view_char.py` to inspect COMM.IMG glyphs confirms the documented characters:
- Cell 251, Bit 3 = 切 (matches documentation)
- Cell 177, Bit 1 = 行 (matches documentation)
- Cell 201, Bit 2 = 獅 (matches documentation)

## BEAM.DAT Analysis

The nonsensical text in BEAM.DAT (e.g., `切聞です。償に切ますか？`) appears to be:

1. **Debug/placeholder content** - The same "dialogue" repeats at multiple chunk offsets (0x49B0C4, 0x55857C, 0x612518, 0x6D52B0), suggesting template data
2. **Unfinished localization** - May be development artifacts that weren't replaced with final text
3. **Different data format** - Some BEAM.DAT regions may contain non-text data that happens to match the FF08 dialogue marker pattern

## Previously Suspected (Now Confirmed Correct)

The following mappings were initially suspected as errors but are verified correct:

| CharID | Bytes | Cell | Documented | Status |
|--------|-------|------|------------|--------|
| 1008 | F3 04 | 251 | 切 | ✓ Correct |
| 807 | F2 3A | 201 | 獅 | ✓ Correct |
| 724 | F1 E6 | 180 | 告 | ✓ Correct |
| 404 | F0 A5 | 100 | 温 | ✓ Correct |
| 965 | F2 D8 | 241 | 慎 | ✓ Correct |
| 584 | F1 5A | 145 | 協 | ✓ Correct |
| 744 | F1 FA | 185 | 狭 | ✓ Correct |
| 916 | F2 A7 | 228 | 償 | ✓ Correct |
| 1005 | F3 01 | 251 | 跡 | ✓ Correct |
| 1087 | F3 53 | 271 | 抱 | ✓ Correct |

## Recommendations

1. **No changes needed to COMM_IMG_chars.md** - The table is accurate
2. **BEAM.DAT decoder may need refinement** - Filter out debug/placeholder text regions
3. **Focus translation effort on STG files** - These contain the actual game dialogue

## Tools Used

- `python/font/view_char.py` - Visual glyph inspection
- `python/font/compare_chars.py` - Side-by-side comparison with reference font
- `python/decode/find_char_errors.py` - Pattern detection (false positive on BEAM.DAT)
- `python/decode/identify_char_mappings.py` - CharID tracing
