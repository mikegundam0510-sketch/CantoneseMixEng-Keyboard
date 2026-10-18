"""One fixed conservative tail-completion study; no fitting or outcome grid."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from report_prefix_retrieval import compare

BASELINE = 'aedb58c3600870aca00c44fc26c864a5b1eaef78'
DATA = ROOT / 'tools/data/tail_supplement'
WORK = ROOT / '.native/tail-supplement-20261018'
REPORTS = ROOT / 'tools/reports/tail-supplement-2026-10-18'
CASES = ROOT / 'tools/data/context_search/calibration1450.tsv'
BEFORE = ROOT / 'tools/reports/pinned-head-2026-10-17/calibration1450.tsv'
GENERATED = ROOT / 'tools/reports/code-generator-2026-10-17/teacher-generated.tsv'
SOURCES = [Path(__file__).parent / name for name in
           ('study.py', 'TailSupplement.java', 'NativeEvaluation.java', 'PolicyTest.java')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        out.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify():
    protocol = json.loads((DATA / 'protocol.json').read_text())
    seal = json.loads((DATA / 'seal.json').read_text())
    if sha(DATA / 'protocol.json') != seal['protocol_sha256']:
        raise ValueError('Protocol changed')
    for name, wanted in protocol['sha256'].items():
        if sha(ROOT / name) != wanted:
            raise ValueError('Frozen source/input changed: ' + name)
    return protocol


def prepare():
    if DATA.exists() or WORK.exists() or REPORTS.exists():
        raise ValueError('Preserve completed work; use separately declared paths for a new study')
    # The previous experiment is immutable. Cached ordinary generation is used
    # only on the identical known inputs, never as an independent evaluation.
    previous = json.loads((ROOT / 'tools/data/code_generator/inference-freeze.json').read_text())
    for name, wanted in previous['sha256'].items():
        if sha(ROOT / name) != wanted:
            raise ValueError('Previous generation freeze changed: ' + name)
    tree = subprocess.check_output(['git', 'rev-parse', BASELINE + ':app'], cwd=ROOT, text=True).strip()
    if tree != '8f31d86ad532f57278669629b642dbafa16c4acc':
        raise ValueError('Parent app differs from the ordinary generation baseline')
    inputs = [CASES, BEFORE, GENERATED, ROOT / 'tools/data/code_generator/models/teacher.npz',
              ROOT / 'tools/data/code_generator/codes.json', ROOT / 'tools/data/code_generator/inference-freeze.json',
              ROOT / 'tools/data/prefix_language/reserve.tsv',
              ROOT / 'tools/reports/pinned-head-2026-10-17/guard3893.tsv',
              ROOT / '.native/joint-ranking-20261015/guard-cases3893.tsv']
    protocol = dict(
        parent_revision=BASELINE, parent_app_tree=tree, arms=['teacher-native-tail-only'],
        source_choice='Fixed teacher checkpoint: the already observed generator recovers20 parent-missing targets versus contrast17. This is informed by known calibration, not a fresh independent result. No refitting or model/source grid.',
        policy='Native prefix min(18,parent-size) stays byte/order identical. Fewer than5 native candidates, interruption, unavailable proposals or explicit personal preference bypass. Compare original slots19/20 and at most20 unique new exact-code teacher proposals, on the same whole-text native score. Select at most2 final slots; native-before-proposal ties. Preserve surviving native relative order. Shorter lists may append at most2. Total display<=20. No post-outcome threshold or slot change.',
        score='QuickDecoder.languageScore(context,text) + SentenceRanker.score(context,text) + PhraseRelationRanker.alignedCorrection(raw(context,text),raw(context,original-head)). All existing bundled models and public whole-text scores. No new neural ranking, no lattice token priors, no personal bonuses. Not claimed identical to the internal lattice path score.',
        calibration='Known1450, target-free predictions before labels joined: exact first18 retention, first/top5 counts unchanged, new150 and old1300 separately top20 nondecreasing, aggregate top20 gain, each named set top20 nondecreasing. Count gains AND losses. No 40-item union counted as display accuracy.',
        later_gates='Only if calibration qualifies: exact Java generator port/parity and optional fallback/personal/mixed protection,3893 aggregate+each-set nondecrease at first/top5/top20, Single32, exact wired Android unit/Lint, same-JVM30warm11 sixcodes wall/CPU ratio<=1.2. Source/model/class freeze then one independent parent/candidate500 evaluation with no first/top5/top20 loss and a top20 gain. No adoption before all gates; stop on an earlier failed gate.',
        reserve='prefix_language/reserve500 remains unused unless every preceding gate passes. The earlier context_search500 is already observed and will not be decoded again.',
        delivery='No APK. Preserve0.6.39/code46, signing, local learning and Fold7. Failed candidate remains research-only; push auditable results to main.',
        sha256={str(path.relative_to(ROOT)): sha(path) for path in SOURCES + inputs})
    write(DATA / 'protocol.json', protocol)
    write(DATA / 'seal.json', dict(protocol_sha256=sha(DATA / 'protocol.json'), before_outcomes=True))
    WORK.mkdir(parents=True)
    REPORTS.mkdir(parents=True)
    # Deliberately strip both gold and stored target rank from prediction input.
    cases, parent, generated = [p.read_text().splitlines() for p in (CASES, BEFORE, GENERATED)]
    if not len(cases) == len(parent) == len(generated) == 1450:
        raise ValueError('Partial known inputs')
    with (WORK / 'inputs.tsv').open('x') as out:
        for case, old, new in zip(cases, parent, generated):
            f, b, g = case.split('\t'), old.split('\t'), new.split('\t')
            if not f == b[:4] == g[:4]:
                raise ValueError('Cached input identity mismatch')
            out.write('\t'.join(f[:3] + [b[5], g[5]]) + '\n')
    native = WORK / 'native'
    native.mkdir()
    archive = subprocess.check_output(['git', 'archive', BASELINE, 'app/src/main/java', 'app/src/main/assets'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as data:
        data.extractall(native, filter='data')
    subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(native / 'app/src/main/java'),
                    '-d', str(native / 'classes')] + [str(p) for p in SOURCES if p.suffix == '.java'], check=True)
    result = subprocess.check_output(['java', '-cp', str(native / 'classes'),
                                      'hk.cantonesemixeng.keyboard.PolicyTest'], text=True)
    (REPORTS / 'policy-checks.txt').write_text(result)
    write(DATA / 'inference-freeze.json', dict(protocol_sha256=sha(DATA / 'protocol.json'),
        sha256={str(path.relative_to(ROOT)): sha(path) for path in
                [WORK / 'inputs.tsv'] + sorted((native / 'classes').rglob('*.class'))
                + sorted((native / 'app/src/main/assets').rglob('*')) if path.is_file()}))
    print(result.strip(), 'protocol sealed; no calibration predictions yet')


def run():
    verify()
    freeze = json.loads((DATA / 'inference-freeze.json').read_text())
    for name, wanted in freeze['sha256'].items():
        if sha(ROOT / name) != wanted:
            raise ValueError('Inference changed: ' + name)
    output = WORK / 'predictions.tsv'
    if output.exists() or (WORK / 'predictions.pending.tsv').exists():
        raise ValueError('Preserve existing predictions')
    native = WORK / 'native'
    subprocess.run(['java', '-Xmx1g', '-cp', str(native / 'classes'),
                    'hk.cantonesemixeng.keyboard.NativeEvaluation', str(native / 'app/src/main/assets'),
                    str(WORK / 'inputs.tsv'), str(WORK / 'predictions.pending.tsv'),
                    str(REPORTS / 'scores.tsv')], check=True)
    (WORK / 'predictions.pending.tsv').rename(output)


def report():
    verify()
    cases, predictions, parent = [p.read_text().splitlines() for p in (CASES, WORK / 'predictions.tsv', BEFORE)]
    if len(cases) != len(predictions):
        raise ValueError('Partial native output')
    changed = additions = removals = 0
    output = REPORTS / 'calibration1450.tsv'
    with output.open('x') as out:
        for case, predicted, old in zip(cases, predictions, parent):
            f, p, b = case.split('\t'), predicted.split('\t'), old.split('\t')
            if f[:3] != p[:3]:
                raise ValueError('Prediction identity differs')
            before = b[5].split('|') if b[5] else []
            values = p[3].split('|') if p[3] else []
            n = min(18, len(before))
            if before[:n] != values[:n] or len(set(values) - set(before)) > 2:
                raise ValueError('Prefix/slot contract failed')
            changed += before != values
            additions += len(set(values) - set(before))
            removals += len(set(before) - set(values))
            rank = values.index(f[3]) + 1 if f[3] in values else 0
            out.write(case + '\t' + str(rank) + '\t' + p[3] + '\n')
    result = compare(CASES, BEFORE, output)
    result['baseline_revision'] = BASELINE
    groups = result['per_set']
    new = [v for k, v in groups.items() if k == 'context-search:validation']
    old = [v for k, v in groups.items() if k != 'context-search:validation']
    result['gates'] = dict(
        all_original_first18_identical=True,
        first_top5_counts_unchanged=all(result['before'][k] == result['after'][k] for k in ('top1', 'top5')),
        new150_top20_nondecreasing=sum(v['after']['top20'] for v in new) >= sum(v['before']['top20'] for v in new),
        old1300_top20_nondecreasing=sum(v['after']['top20'] for v in old) >= sum(v['before']['top20'] for v in old),
        aggregate_top20_gain=result['after']['top20'] > result['before']['top20'],
        every_set_top20_nondecreasing=all(v['after']['top20'] >= v['before']['top20'] for v in groups.values()))
    result['qualified'] = all(result['gates'].values())
    result['display_changes'] = dict(cases=changed, additions=additions, removals=removals,
                                     protected_native_prefix=18, maximum_new_per_case=2)
    result['known_calibration_not_independent'] = True
    write(REPORTS / 'calibration1450.json', result)
    write(DATA / 'selection.json', dict(selected='teacher-native-tail-only' if result['qualified'] else None,
        gates=result['gates'], before=result['before'], after=result['after'], paired=result['paired'],
        reserve500_decoded=False, decision='Proceed to exact Java generator and fixed guards' if result['qualified']
        else 'Reject this fixed tail policy; retain production; preserve independent500. No outcome tuning.'))
    print(json.dumps({k: result[k] for k in ('before', 'after', 'paired', 'gates', 'qualified', 'display_changes')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run', 'report'])
    mode = parser.parse_args().mode
    {'prepare': prepare, 'run': run, 'report': report}[mode]()
