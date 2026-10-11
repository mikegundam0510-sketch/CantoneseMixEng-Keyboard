"""Summarize observations from decoder_diagnostics.py, using fixed public cases.

The terminal blocker is the furthest observed gold frontier, not proof that a
particular earlier prune caused every possible tokenization to fail. A generated
prefix can skip intermediate characters through an attested multi-character word.
No production decoder, test case, or private phone log is changed by this tool.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


def summarize(path):
    reasons = Counter()
    blockers = Counter()
    characters = Counter()
    character_ranks = defaultdict(set)
    stages = Counter()
    missing = []
    exact = 0
    cases = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 9:
            raise ValueError("Expected nine columns including prefix events")
        context, code, target, rank, raw, reason, _, matches, trace = fields
        cases += 1
        exact += matches == "true"
        reasons[reason] += 1
        if int(rank):
            continue
        events = [event.split(",") for event in trace.split(";") if event]
        generated = [(int(e[1]), e[2]) for e in events if e[0] == "G"]
        consumed = [(int(e[1]), e[2]) for e in events
                    if e[0] == "B" and e[4] == "true"]
        frontier = max(generated, key=lambda p: len(p[1]), default=(0, ""))
        active = max(consumed, key=lambda p: len(p[1]), default=(0, ""))
        losses = [e for e in events if e[0] in ("I", "B")
                  and e[2] == frontier[1] and e[4] == "false"]
        omissions = [e for e in events if e[0] == "O" and e[2] == active[1]
                     and e[5] == "false" and len(e[4]) == 1]
        if matches != "true":
            blocker = "inexact_target_code"
        elif reason != "not_generated":
            blocker = reason
        elif len(frontier[1]) > len(active[1]) and losses:
            blocker = "prefix_pruned"
            stages[",".join(sorted({e[0] for e in losses}))] += 1
        elif omissions:
            blocker = "choice_cutoff"
            for event in omissions:
                characters[event[4]] += 1
                character_ranks[event[4]].add(int(event[7]))
        else:
            blocker = "unresolved_not_generated"
        blockers[blocker] += 1
        hints = [e[2] for e in events if e[0] == "H"
                 and int(e[1]) == frontier[0]]
        first_loss = next((e for e in events if e[0] in ("I", "B")
                           and e[4] == "false"), None)
        missing.append({
            "context": context,
            "code": code,
            "target": target,
            "raw_final_rank": int(raw),
            "terminal_blocker": blocker,
            "furthest_generated": {"code_position": frontier[0], "text": frontier[1]},
            "furthest_consumed": {"code_position": active[0], "text": active[1]},
            "terminal_prune_observations": losses,
            "omitted_next_characters": omissions,
            "existing_hints_at_frontier": hints,
            "first_observed_prune_loss": first_loss,
        })
    return {
        "input": str(path),
        "cases": cases,
        "valid_exact_target_codes": exact,
        "coarse_reasons": dict(reasons),
        "missing_cases": sum(blockers.values()),
        "terminal_blockers": dict(blockers),
        "choice_cutoff_characters": dict(characters),
        "choice_cutoff_dictionary_ranks": {c: sorted(ranks) for c, ranks in character_ranks.items()},
        "prefix_prune_stages": dict(stages),
        "interpretation": "Observed terminal frontiers only; an earlier loss can be bypassed by another word tokenization. Gold text is used only for diagnostics, never production search.",
        "missing": missing,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = summarize(args.input)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "missing"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
