#!/usr/bin/env python3
"""
Batch preparation for STG file translation.

Compares source decoded STG files (output/decoded/stg/*.txt) with existing
Korean translations (translated/ko/*.txt), determines where translation stopped,
and splits remaining untranslated source lines into batch files of ~30 dialogue
lines each.

Output:
  translated/ko/batches/<STG_NAME>_batch_NNN.txt  (source Japanese lines)
  translated/ko/batches/manifest.json             (batch tracking)
"""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(BASE_DIR, "output", "decoded", "stg")
KO_DIR = os.path.join(BASE_DIR, "translated", "ko")
BATCH_DIR = os.path.join(KO_DIR, "batches")

BATCH_SIZE = 30  # dialogue lines per batch

OFFSET_RE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)")
CONTEXT_RE = re.compile(r"^\s*---\s*context:")

STG_NAMES = [
    "S100", "S200", "S300", "S400", "S500", "S600", "S700",
    "S800", "S900", "SA00", "SB00", "SC00", "SD00", "SE00",
    "SF00", "SG00", "SH00", "SI00", "SJ00",
]


def extract_offsets(filepath):
    """Extract all hex offsets from a file, returning a set."""
    offsets = set()
    if not os.path.exists(filepath):
        return offsets
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            m = OFFSET_RE.match(line)
            if m:
                offsets.add(m.group(1))
    return offsets


def read_source_lines(filepath):
    """Read source file and return list of (offset_or_none, line) tuples.

    Dialogue lines have an offset; context/blank/header lines have None.
    """
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = OFFSET_RE.match(line)
            if m:
                entries.append((m.group(1), line))
            elif CONTEXT_RE.match(line):
                entries.append((None, line))  # context separator
            # skip header and blank lines
    return entries


def find_untranslated(src_entries, ko_offsets):
    """Return the suffix of src_entries starting after the last translated offset.

    Includes context lines that appear between untranslated dialogue lines.
    """
    # Find the index of the last source entry whose offset is in ko_offsets
    last_translated_idx = -1
    for i, (offset, _line) in enumerate(src_entries):
        if offset is not None and offset in ko_offsets:
            last_translated_idx = i

    # Everything after last_translated_idx is untranslated
    remaining = src_entries[last_translated_idx + 1:]
    return remaining


def split_into_batches(entries, batch_size):
    """Split entries into batches of approximately batch_size dialogue lines.

    Context lines are attached to the batch of the dialogue that follows them.
    """
    batches = []
    current_batch = []
    dialogue_count = 0

    for offset, line in entries:
        if offset is not None:
            # This is a dialogue line
            dialogue_count += 1
            current_batch.append(line)
            if dialogue_count >= batch_size:
                batches.append(current_batch)
                current_batch = []
                dialogue_count = 0
        else:
            # Context line - attach to current batch
            current_batch.append(line)

    # Don't forget the last batch
    if current_batch:
        # Only add if there's at least one dialogue line
        has_dialogue = any(OFFSET_RE.match(l) for l in current_batch)
        if has_dialogue:
            batches.append(current_batch)

    return batches


def main():
    os.makedirs(BATCH_DIR, exist_ok=True)

    manifest = {
        "batch_size": BATCH_SIZE,
        "files": {},
        "batches": [],
    }

    total_batches = 0
    total_remaining = 0

    for name in STG_NAMES:
        src_path = os.path.join(SRC_DIR, f"{name}_STG.txt")
        ko_path = os.path.join(KO_DIR, f"{name}_STG.txt")

        if not os.path.exists(src_path):
            continue

        # Get translated offsets (check main file + any chunk files)
        ko_offsets = extract_offsets(ko_path)
        # Also check chunk files like S800_chunk2.txt
        for extra in os.listdir(KO_DIR):
            if extra.startswith(name) and extra != f"{name}_STG.txt" and extra.endswith(".txt"):
                ko_offsets |= extract_offsets(os.path.join(KO_DIR, extra))

        # Read source and find untranslated entries
        src_entries = read_source_lines(src_path)
        untranslated = find_untranslated(src_entries, ko_offsets)

        # Count actual dialogue lines
        dialogue_lines = sum(1 for off, _ in untranslated if off is not None)

        if dialogue_lines == 0:
            print(f"  {name}: fully translated ({len(ko_offsets)} dialogues)")
            manifest["files"][name] = {
                "status": "complete",
                "src_dialogues": sum(1 for off, _ in src_entries if off is not None),
                "translated": len(ko_offsets),
                "remaining": 0,
                "batch_count": 0,
            }
            continue

        total_remaining += dialogue_lines

        # Split into batches
        batches = split_into_batches(untranslated, BATCH_SIZE)

        file_info = {
            "status": "partial",
            "src_dialogues": sum(1 for off, _ in src_entries if off is not None),
            "translated": len(ko_offsets),
            "remaining": dialogue_lines,
            "batch_count": len(batches),
            "batch_indices": [],
        }

        for i, batch_lines in enumerate(batches):
            batch_idx = total_batches
            batch_name = f"{name}_batch_{i:03d}"
            batch_path = os.path.join(BATCH_DIR, f"{batch_name}.txt")

            with open(batch_path, "w", encoding="utf-8") as f:
                for line in batch_lines:
                    f.write(line + "\n")

            batch_dialogue_count = sum(1 for l in batch_lines if OFFSET_RE.match(l))

            manifest["batches"].append({
                "id": batch_idx,
                "name": batch_name,
                "stg_name": name,
                "file": f"{batch_name}.txt",
                "dialogue_count": batch_dialogue_count,
                "status": "pending",
            })

            file_info["batch_indices"].append(batch_idx)
            total_batches += 1

        manifest["files"][name] = file_info
        print(f"  {name}: {dialogue_lines} dialogues remaining -> {len(batches)} batches")

    manifest["total_batches"] = total_batches
    manifest["total_remaining_dialogues"] = total_remaining

    manifest_path = os.path.join(BATCH_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\nTotal: {total_remaining} dialogue lines in {total_batches} batches")
    print(f"Manifest written to: {manifest_path}")
    print(f"Batch files written to: {BATCH_DIR}/")


if __name__ == "__main__":
    main()
