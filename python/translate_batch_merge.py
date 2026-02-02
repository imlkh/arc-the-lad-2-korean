#!/usr/bin/env python3
"""
Merge completed batch translations into final Korean translation files.

Reads the manifest to find completed batches for each STG file,
concatenates them in order, and appends to the existing translated/ko/*.txt files.

Usage:
  python3 python/translate_batch_merge.py [--dry-run]
"""

import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KO_DIR = os.path.join(BASE_DIR, "translated", "ko")
BATCH_DIR = os.path.join(KO_DIR, "batches")
MANIFEST_PATH = os.path.join(BATCH_DIR, "manifest.json")

OFFSET_RE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)")


def load_manifest():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def count_dialogues(filepath):
    """Count dialogue lines (lines starting with offset) in a file."""
    count = 0
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if OFFSET_RE.match(line):
                count += 1
    return count


def read_file_content(filepath):
    """Read file content, stripping trailing whitespace."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def main():
    dry_run = "--dry-run" in sys.argv

    if not os.path.exists(MANIFEST_PATH):
        print("Error: manifest.json not found. Run translate_batch_prep.py first.")
        sys.exit(1)

    manifest = load_manifest()

    # Group batches by STG name
    batches_by_stg = {}
    for batch in manifest["batches"]:
        stg = batch["stg_name"]
        if stg not in batches_by_stg:
            batches_by_stg[stg] = []
        batches_by_stg[stg].append(batch)

    # Sort batches within each group by their ID (which is creation order)
    for stg in batches_by_stg:
        batches_by_stg[stg].sort(key=lambda b: b["id"])

    total_merged = 0
    total_gaps = 0

    for stg_name, file_info in manifest["files"].items():
        if file_info["status"] == "complete":
            print(f"  {stg_name}: already fully translated, skipping")
            continue

        if stg_name not in batches_by_stg:
            continue

        batches = batches_by_stg[stg_name]
        ko_path = os.path.join(KO_DIR, f"{stg_name}_STG.txt")

        # Check batch statuses
        done_batches = [b for b in batches if b["status"] == "done"]
        pending_batches = [b for b in batches if b["status"] == "pending"]
        failed_batches = [b for b in batches if b["status"] not in ("done", "pending")]

        if pending_batches:
            print(f"  {stg_name}: {len(pending_batches)} batches still pending")
            total_gaps += len(pending_batches)

        if failed_batches:
            print(f"  {stg_name}: {len(failed_batches)} batches failed!")
            total_gaps += len(failed_batches)

        if not done_batches:
            print(f"  {stg_name}: no completed batches to merge")
            continue

        # Check for gaps in the sequence (only merge contiguous done batches from start)
        contiguous_done = []
        for batch in batches:
            if batch["status"] == "done":
                contiguous_done.append(batch)
            else:
                # Stop at first gap to maintain ordering
                break

        if len(contiguous_done) < len(done_batches):
            print(f"  {stg_name}: WARNING - {len(done_batches) - len(contiguous_done)} "
                  f"completed batches after gaps will be skipped")

        # Read and concatenate batch outputs
        merged_content = []
        merged_dialogues = 0

        for batch in contiguous_done:
            output_file = os.path.join(BATCH_DIR, batch["name"] + "_ko.txt")
            if not os.path.exists(output_file):
                print(f"  {stg_name}: ERROR - output file missing: {output_file}")
                total_gaps += 1
                break

            content = read_file_content(output_file)
            batch_dialogues = count_dialogues(output_file)
            merged_content.append(content.rstrip("\n"))
            merged_dialogues += batch_dialogues

        if not merged_content:
            continue

        merged_text = "\n".join(merged_content) + "\n"

        if dry_run:
            print(f"  {stg_name}: would append {merged_dialogues} dialogues "
                  f"({len(contiguous_done)}/{len(batches)} batches)")
        else:
            # Append to existing ko file
            with open(ko_path, "a", encoding="utf-8") as f:
                f.write(merged_text)

            print(f"  {stg_name}: appended {merged_dialogues} dialogues "
                  f"({len(contiguous_done)}/{len(batches)} batches)")

        total_merged += merged_dialogues

    print(f"\nTotal: {total_merged} dialogues merged")
    if total_gaps > 0:
        print(f"Gaps: {total_gaps} batches need attention")
    if dry_run:
        print("(dry run - no files modified)")


if __name__ == "__main__":
    main()
