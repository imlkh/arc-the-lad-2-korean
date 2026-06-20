#!/usr/bin/env python3
"""Phase-2: scan-rule discovery for decoder-missed dialogue.

Premise (from coverage spec): the template-driven decoder (scan_stg) misses real
dialogue that lives in the text region but is not template-anchored. We use the
dialogue we already found (K = scan_stg output) as ground truth to DISCOVER and
VALIDATE locator rules, then apply the validated rule to surface missed dialogue.

Honesty contract: every candidate rule is scored on a HELD-OUT half of K
(precision = rule-located strings that are known-real / all rule-located strings),
so a rule cannot be "confirmed" by the offsets that produced it. Output reports the
discovered rule, its held-out precision/recall, and the deduped missed entries.

Usage:
    python python/tools/discover_scan_rules.py            # all stages
    python python/tools/discover_scan_rules.py S700       # one stage
"""
import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "python" / "decode"))
import decode_text as dt  # noqa: E402

STAGES = [f"S{c}00" for c in
          ["1", "2", "3", "4", "5", "6", "7", "8", "9",
           "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

_STRUCT = re.compile(r"\[br\]|\[box:|\[FF:|\[name:|\[item:|\[num:")
_PARTICLES = set("はがをにのへともや")


def real_kana(text: str) -> bool:
    return any(0x3041 <= ord(c) <= 0x3096 or 0x30A1 <= ord(c) <= 0x30FA
               for c in text)


# ---- candidate locator rules (feature predicates on a decoded run) ----
# A rule decides, for a cleanly-decoded text-region run, whether it looks like
# real dialogue. Discovery picks the rule with the best held-out precision while
# retaining enough recall on K.

def rule_struct(text: str) -> bool:
    """Has a structural control code AND real kana."""
    return bool(_STRUCT.search(text)) and real_kana(text)


def rule_grammar(text: str) -> bool:
    """Long real-kana run with a grammatical particle (no control code needed)."""
    kana = sum(1 for c in text if real_kana(c))
    return kana >= 8 and any(c in _PARTICLES for c in text)


def rule_struct_or_grammar(text: str) -> bool:
    return rule_struct(text) or rule_grammar(text)


CANDIDATE_RULES = {
    "struct": rule_struct,
    "grammar": rule_grammar,
    "struct_or_grammar": rule_struct_or_grammar,
}


def _scan_runs(data, decode_table):
    """Yield (offset, text) for every cleanly-decoding non-zero run in every
    chunk's text region. This is the universe the rules filter."""
    for start, end, _chunk in dt._get_chunk_text_regions(len(data)):
        pos = start
        while pos < end:
            if data[pos] == 0x00:
                pos += 1
                continue
            text, consumed = dt.decode_string(data, pos, decode_table)
            yield pos, text
            pos += max(consumed, 1)


def discover_for_stage(stage, decode_table):
    """Returns dict with the chosen rule, held-out metrics, and missed entries."""
    binary = GAME_DIR / f"{stage}.STG"
    if not binary.exists():
        return None
    data = binary.read_bytes()

    # K = ground-truth real dialogue offsets from the existing decoder.
    dialogues, _t, _s = dt.scan_stg(data, decode_table, filter_garbage=True)
    K = sorted(d[0] for d in dialogues)
    if len(K) < 20:
        return {"stage": stage, "rule": None, "reason": "too few K", "missed": []}

    # Deterministic train/held-out split (even index = train, odd = held-out).
    train = set(K[0::2])
    heldout = set(K[1::2])

    runs = list(_scan_runs(data, decode_table))
    by_off = {off: text for off, text in runs}

    # Evaluate each candidate rule on the held-out set:
    #   recall  = held-out K offsets the rule fires on / |held-out K|
    #   precision (proxy) = rule-fired runs that are real (in K OR not garbage)
    #                       / all rule-fired runs
    best = None
    for name, fn in CANDIDATE_RULES.items():
        fired = [(off, text) for off, text in runs if fn(text)]
        if not fired:
            continue
        ho_hit = sum(1 for off in heldout if off in by_off and fn(by_off[off]))
        recall = ho_hit / len(heldout) if heldout else 0.0
        real = sum(1 for off, text in fired
                   if off in train or off in heldout or not dt._is_garbage_text(text))
        precision = real / len(fired)
        score = (precision, recall)
        if best is None or score > best["score"]:
            best = {"name": name, "fn": fn, "precision": precision,
                    "recall": recall, "score": score, "fired": fired}

    if best is None:
        return {"stage": stage, "rule": None, "reason": "no rule fired", "missed": []}

    # Apply chosen rule: missed = rule-fired runs NOT already in K, that decode to
    # real dialogue and are not garbage. Dedup by text within the stage.
    kset = set(K)
    seen = set()
    missed = []
    for off, text in best["fired"]:
        if off in kset:
            continue
        if dt._is_garbage_text(text):
            continue
        key = text.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        missed.append((off, text))
    missed.sort()
    return {"stage": stage, "rule": best["name"], "precision": best["precision"],
            "recall": best["recall"], "k": len(K), "missed": missed}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    stages = [a.upper() for a in argv] if argv else STAGES
    table = dt.build_decode_table()
    print(f"{'Stage':<7}{'Rule':<18}{'HOprec':>8}{'HOrec':>8}{'K':>6}{'Missed(uniq)':>14}")
    grand = 0
    for stage in stages:
        r = discover_for_stage(stage, table)
        if r is None:
            print(f"{stage:<7}{'(no binary)':<18}")
            continue
        if not r.get("rule"):
            print(f"{stage:<7}{'(' + r.get('reason', 'n/a') + ')':<18}")
            continue
        n = len(r["missed"])
        grand += n
        print(f"{stage:<7}{r['rule']:<18}{r['precision']:>8.3f}{r['recall']:>8.3f}"
              f"{r['k']:>6}{n:>14}")
    print(f"{'TOTAL':<7}{'':<18}{'':>8}{'':>8}{'':>6}{grand:>14}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
