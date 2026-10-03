#!/usr/bin/env python3
"""Rebuild offline English words from the pinned, MIT-licensed Wordnik list."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app/src/main/assets"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wordlist", type=Path, help="wordlist-20210729.txt at the revision in english-provenance.json")
    args = parser.parse_args()
    provenance = json.loads((ASSETS / "english-provenance.json").read_text())
    if hashlib.sha256(args.wordlist.read_bytes()).hexdigest() != provenance["source_sha256"]:
        parser.error("Input does not match the pinned Wordnik source SHA-256")
    priorities = [s.strip() for s in (ROOT / "tools/english-priority.txt").read_text().splitlines() if s.strip() and not s.startswith("#")]
    words = [s.strip().strip('"') for s in args.wordlist.read_text().splitlines()]
    output = list(dict.fromkeys(priorities + [s for s in words if s.isascii() and s.isalpha() and len(s) <= 20]))
    header = "# Hand-authored priority words, followed by Wordnik MIT-licensed wordlist.\n"
    header += f"# Wordnik revision {provenance['revision']}; see licenses/WORDNIK-LICENSE.txt.\n"
    (ASSETS / "english.txt").write_text(header + "\n".join(output) + "\n")
    assert len(output) == provenance["entries"]
    print(f"Wrote {len(output):,} words")


if __name__ == "__main__":
    main()
