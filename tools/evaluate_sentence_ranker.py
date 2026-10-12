#!/usr/bin/env python3
"""Select a fixed whole-candidate strength on validation only, then evaluate guards."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from train_sentence_ranker import correction, encode
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

DATA = ROOT / 'tools/data/sentence_ranking'


def evaluate(weights, scored, strength, output, gate='conservative'):
    grouped = defaultdict(list)
    for line in scored.read_text().splitlines():
        fields = line.split('\t')
        source, context, code, gold, rank, candidates, scores = fields[:7]
        if gate != 'none' and len(fields) != 8: raise ValueError('Structural support annotation required')
        values = candidates.split('|') if candidates else []
        numbers = [float.fromhex(s) for s in scores.split('|')] if scores else []
        if len(values) != len(numbers): raise ValueError('Incomplete scores')
        adjusted = {v: s + correction(weights, context, v, strength) for v, s in zip(values, numbers)}
        pin = False
        if gate != 'none' and values:
            support = [float.fromhex(s) for s in fields[7].split('|')]
            if len(support) != len(values): raise ValueError('Incomplete structural support')
            pin = support[0] > 0 and gate == 'conservative'
            if support[0] > 0 and gate == 'weak':
                import math
                ceiling = math.nextafter(adjusted[values[0]], -math.inf)
                for value, evidence in zip(values, support):
                    if evidence < support[0]: adjusted[value] = min(adjusted[value], ceiling)
        updated = ([values[0]] + sorted(values[1:],key=lambda v:-adjusted[v]) if pin else
                   sorted(values,key=lambda v:-adjusted[v])) if strength else list(values)
        if set(values) != set(updated) or len(values) != len(updated): raise AssertionError('Candidate pool changed')
        new_rank = updated.index(gold) + 1 if gold in updated else 0
        name = source.split(':', 1)[-1]
        grouped[name].append((context, code, gold, new_rank, updated))
    output.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, rows in grouped.items():
        path = output / f'{name}-{strength:g}.tsv'
        path.write_text(''.join('\t'.join((c, code, gold, str(rank), '|'.join(values))) + '\n'
                                for c, code, gold, rank, values in rows))
        ranks = [r[3] for r in rows]
        result[name] = dict(cases=len(ranks), top1=sum(r == 1 for r in ranks),
                            top5=sum(0 < r <= 5 for r in ranks), top20=sum(r > 0 for r in ranks),
                            mrr=sum(1 / r for r in ranks if r) / len(ranks), output_sha256=digest(path))
    return result


def select(weights_path, scored, output, gate='conservative'):
    weights = json.loads(weights_path.read_text())
    protocol = json.loads((DATA / 'protocol.json').read_text())
    results = {s: evaluate(weights, scored, s, output / 'validation', gate) for s in [0] + protocol['strength_grid']}
    if set(results[0]) != {'authored60', 'natural200', 'public200'}: raise ValueError('Incorrect validation sets')
    eligible = [s for s in protocol['strength_grid'] if all(results[s][n][k] >= results[0][n][k]
                 for n in results[0] for k in ('top1', 'top5'))]
    strength = max(eligible, key=lambda s: (sum(v['mrr'] for v in results[s].values()), -s)) if eligible else 0
    report = {'validation': results, 'eligible_strengths': eligible, 'selected_strength': strength,
              'protocol_sha256': digest(DATA / 'protocol.json'), 'weights_sha256': digest(weights_path),
              'validation_scored_sha256': digest(scored), 'structural_gate': gate,
              'note': 'Written before followup guard decoding; earlier observed guards are diagnostic regressions.'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'selection.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'sentence_ranker.b64').write_bytes(encode(weights, strength))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('weights', type=Path); p.add_argument('scored', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--guards', action='store_true')
    p.add_argument('--gate', choices=('none','weak','conservative'), default='conservative')
    a = p.parse_args()
    if a.guards:
        decision = json.loads((a.output / 'selection.json').read_text())
        weights = json.loads(a.weights.read_text())
        before = evaluate(weights, a.scored, 0, a.output / 'guards', a.gate)
        after = evaluate(weights, a.scored, decision['selected_strength'], a.output / 'guards', a.gate)
        failures = [n for n in ('fresh100', 'natural200', 'old600', 'daily32', 'completion16','handover','authored70','followup100') if n in before
                    if any(after[n][k] < before[n][k] for k in ('top1', 'top5'))]
        report = {'before': before, 'after': after, 'guard_failures': failures,
                  'guard_scored_sha256': digest(a.scored), 'candidate_membership_unchanged': True}
        (a.output / 'guard-report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    else:
        print(json.dumps(select(a.weights, a.scored, a.output, a.gate), indent=2))
