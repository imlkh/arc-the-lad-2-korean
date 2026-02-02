#!/usr/bin/env python3
"""
Batch translation runner for Claude Code.

THIS FILE IS NOT A PYTHON SCRIPT TO RUN DIRECTLY.
It contains the instructions and prompt template for Claude Code to execute.

Usage in Claude Code:
  1. First run: python3 python/translate_batch_prep.py
  2. Then tell Claude Code: "Run the batch translation using python/translate_batch_run.py"
  3. Claude Code will read this file, then use the Task tool to spawn subagents
     that translate each batch file.

The subagent workflow:
  - Read a batch file (30 Japanese dialogue lines with context markers)
  - Translate each dialogue line from Japanese to natural Korean
  - Preserve all tags, offsets, opcodes, context separators exactly
  - Write the translated output to <batch_name>_ko.txt
  - Claude Code updates manifest.json to mark the batch as done
"""

# ============================================================
# INSTRUCTIONS FOR CLAUDE CODE (read this file, then follow)
# ============================================================
#
# 1. Read the manifest at: translated/ko/batches/manifest.json
# 2. For each batch with status "pending", spawn a background subagent
#    using the Task tool (subagent_type="general-purpose")
# 3. Run up to 5 subagents in parallel at a time
# 4. After each subagent completes, update manifest.json status to "done"
# 5. Continue until all batches are processed
#
# SUBAGENT PROMPT TEMPLATE (fill in {batch_file} and {output_file}):

SUBAGENT_PROMPT = """
You are translating Japanese dialogue from the PS1 game "Arc the Lad 2" into natural Korean.

Read the file: {batch_file}

This file contains dialogue lines in this format:
  0xOFFSET [0xOPCODE] [script:XX XX]Japanese text here
  0xOFFSET [0xOPCODE] [script:XX XX][box:speech]Japanese text here
  --- context: 0xXXXX -> 0xXXXX ---

TRANSLATION RULES:
1. Translate ONLY the Japanese text portion after the last ] bracket into natural Korean
2. Preserve EXACTLY: hex offsets (0x...), opcodes ([0x...]), [script:...], [box:...], [delay:XX], [opt], [item:XX], [?XXXX] tags
3. Preserve context separator lines (--- context: ...) exactly as-is
4. Preserve \\n line breaks within dialogue text
5. Use natural, conversational Korean appropriate to each character's tone
6. Keep punctuation style consistent (…, ！, ？ become …, !, ?)

CHARACTER NAME MAPPINGS (use these Korean names):
  エルク → 엘크          アーク → 아크
  リーザ → 리자          ククル → 쿠쿠루
  シャンテ → 샨테        ポコ → 포코
  トッシュ → 토슈        ゴーゲン → 고겐
  シュウ → 슈우          イーガ → 이가
  グルガ → 그루가        サニア → 사니아
  ちょこ/チョコ → 쵸코    ヂークベック → 지크벡
  ガルアーノ → 갈아노     ヤグン → 야군
  アンデル → 안델        クライブ → 크라이브
  ヘモジー → 헤모지

PLACE NAME MAPPINGS:
  ロマリア → 로말리아     アルディア → 알디아
  プロディアス → 프로디아스  ミルマーナ → 밀마나
  スメリア → 스메리아     グレイシーヌ → 그레이슈뉴
  パレンシア → 팔렌시아   シルバーノア → 실버노아
  インディゴス → 인디고스  ホルン → 호른

COMMON TERM MAPPINGS:
  精霊 → 정령    魔物 → 마물    聖柩 → 성궤
  闘技場 → 투기장  封印 → 봉인    勇者 → 용사
  魔法 → 마법    仲間 → 동료    武器 → 무기
  防具 → 방구    道具 → 도구    宝物 → 보물

EXAMPLE translations:
  Input:  0x000B4516 [0x8006] [script:16 07]大きな街ね
  Output: 0x000B4516 [0x8006] [script:16 07]큰 거리네

  Input:  0x000BA560 [0x8007] [script:30 07]そう、そのゾンビたちは\\nこの私の生体実験の失敗作
  Output: 0x000BA560 [0x8007] [script:30 07]그래, 그 좀비들은\\n이 나의 생체 실험 실패작

  Input:  --- context: 0x8003 -> 0x8005 ---
  Output: --- context: 0x8003 -> 0x8005 ---

  Input:  0x000BA476 [0x8005] [script:B2 06][box:speech]ちくしょう、弱い奴ほどよく群れやがる！
  Output: 0x000BA476 [0x8005] [script:B2 06][box:speech]젠장, 약한 놈들일수록 잘 몰려다니지!

Now translate ALL lines in the file, writing the complete output to: {output_file}

The output file should contain EVERY line from the input, with Japanese dialogue translated to Korean.
Context separator lines and any other non-dialogue lines should be copied exactly as-is.

Write the complete translated file now.
"""

# After all subagents finish, run: python3 python/translate_batch_merge.py
