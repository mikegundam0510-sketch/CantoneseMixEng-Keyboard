#!/usr/bin/env python3
"""Summarize the frozen500 native comparison without changing any model choice."""
import argparse
import csv
import json
import math
from pathlib import Path
from prepare_tatoeba_corpus import digest
from train_candidate_ranker import matches
from train_phrase_model import ROOT, reverse_codes

DATA = ROOT / 'tools/data/search_alignment'


def metrics(rows):
    ranks = [int(row[4]) for row in rows]
    return dict(cases=len(ranks), top1=sum(r == 1 for r in ranks),
                top5=sum(0 < r <= 5 for r in ranks),
                top20=sum(0 < r <= 20 for r in ranks),
                mrr=sum(1 / r for r in ranks if r) / len(ranks))


def report(before_path, after_path, output):
    selection = json.loads((DATA / 'selection.json').read_text())
    assert digest(DATA / 'heldout.tsv') == selection['heldout_sha256']
    assert digest(DATA / 'protocol.json') == selection['protocol_sha256']
    assert digest(DATA / 'candidate-relation_ranker.b64') == selection['model_sha256']
    cases = list(csv.reader((DATA / 'heldout.tsv').open(), delimiter='\t'))
    before = list(csv.reader(before_path.open(), delimiter='\t'))
    after = list(csv.reader(after_path.open(), delimiter='\t'))
    assert len(cases) == len(before) == len(after) == 500
    reverse = reverse_codes()
    changes = []
    gained = lost = 0
    for case, old, new in zip(cases, before, after):
        assert old[:4] == new[:4] == case
        for row in (old, new):
            assert len(row) == 6
            candidates = row[5].split('|') if row[5] else []
            assert len(candidates) <= 20 and len(set(candidates)) == len(candidates)
            assert all(matches(row[2], text, reverse) for text in candidates)
            rank = candidates.index(row[3]) + 1 if row[3] in candidates else 0
            assert rank == int(row[4])
        rb, ra = int(old[4]), int(new[4])
        gain = int(0 < ra <= 5) - int(0 < rb <= 5)
        gained += gain == 1
        lost += gain == -1
        if rb != ra:
            changes.append(dict(source=case[0], context=case[1], code=case[2],
                                target=case[3], before=rb, after=ra, top5_delta=gain))
    baseline, current = metrics(before), metrics(after)
    discordant = gained + lost
    # Exact paired sign/McNemar test; retained as uncertainty, not an adoption gate.
    p = min(1, 2 * sum(math.comb(discordant, k)
                      for k in range(min(gained, lost) + 1)) / 2 ** discordant)
    result = dict(
        baseline_revision=json.loads((DATA / 'protocol.json').read_text())['baseline_revision'],
        before=baseline, after=current, top5_entered=gained, top5_left=lost,
        top5_percentage_point_gain=100 * (current['top5'] - baseline['top5']) / 500,
        paired_exact_two_sided_p=p, rank_changes=len(changes), changes=changes,
        selection_sha256=digest(DATA / 'selection.json'),
        heldout_sha256=digest(DATA / 'heldout.tsv'),
        before_sha256=digest(before_path), after_sha256=digest(after_path),
        model_sha256=selection['model_sha256'],
        no_post_reserve_model_or_policy_tuning=True,
        exact_codes_and_display_bounds=True,
        independent_gate_passed=(current['top5'] > baseline['top5'] and
                                 current['top1'] >= baseline['top1'] and
                                 current['top20'] >= baseline['top20']),
        limitations='Small dictionary-example gain; paired p exceeds0.05. No general chat-frequency, Fold7 or1.0 claim. Reserve is now observed evaluation material; frozen protocol/selection retain their historical unopened status.')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'changes'}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('before', 'after', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report(args.before, args.after, args.output)
