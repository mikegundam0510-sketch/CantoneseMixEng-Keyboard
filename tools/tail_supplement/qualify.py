"""Parse completed guards and freeze the exact candidate for one unused test."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from study import ROOT,DATA,WORK,REPORTS,BASELINE,sha,write,verify


def guards():
    verify()
    log=(WORK/'single32.log').read_text()
    if 'cases=32 sequence_records=489 legacy=[30, 32, 32] contextual=[32, 32, 32]' not in log:
        raise ValueError('Enabled Single learning failed')
    if len((REPORTS/'single32.tsv').read_text().splitlines())!=32:raise ValueError('Partial Single output')
    protection=(REPORTS/'protection.txt').read_text()
    if 'protection_cases=4 active=true optional_fallback=true legacy_confirmed=true positive_negative_context=true mixed_translation=true' not in protection:
        raise ValueError('Optional/personal/mixed wiring checks failed')
    write(REPORTS/'learning.json',dict(qualified=True,cases=32,legacy=[30,32,32],contextual=[32,32,32],sequence_records=489,
        all_learned_displays_identical_to_parent=True,enabled_protection_cases=4,model_active_in_cold_fixture=True))
    android=WORK/'android';tests=Counter()
    paths=list((android/'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml'))
    if not paths:raise ValueError('Android unit results missing')
    for path in paths:
        node=ET.parse(path).getroot()
        for k in ('tests','failures','errors','skipped'):tests[k]+=int(node.get(k,0))
    if tests['tests']!=222 or any(tests[k] for k in ('failures','errors','skipped')):
        raise ValueError('Android tests failed/partial')
    lint=Counter(n.get('severity') for n in ET.parse(android/'app/build/reports/lint-results-debug.xml').getroot().findall('issue'))
    if lint['Error'] or lint['Fatal']:raise ValueError('Android Lint errors')
    if 'BUILD SUCCESSFUL' not in (WORK/'android-checks-retry.log').read_text():raise ValueError('Android build incomplete')
    if list(android.rglob('*.apk')):raise ValueError('No APK was authorized')
    write(REPORTS/'android.json',dict(qualified=True,unit_tests=dict(tests),lint=dict(lint),apk_produced=False,
        wiring='Exact optional model/service constructor and same Java inference sources as native candidate',
        initial_attempt='Sandbox local wildcard-address denial before build startup; retry with normal local networking succeeded.'))


def timing():
    path=REPORTS/'timing.tsv';rows=[]
    for line in path.read_text().splitlines():
        if not line or line.startswith('#'):continue
        f=line.split('\t');code=f[0];v=list(map(float,f[2:]));bw,aw,bc,ac=v
        rows.append(dict(code=code,letters=int(f[1]),before_wall_median_ms=bw,after_wall_median_ms=aw,
            before_cpu_median_ms=bc,after_cpu_median_ms=ac,wall_ratio=aw/bw,cpu_ratio=ac/bc))
    if len(rows)!=6 or '# warmup=30 samples=11' not in path.read_text():raise ValueError('Quiet timing incomplete')
    maximum=max(max(r['wall_ratio'],r['cpu_ratio']) for r in rows)
    result=dict(warmup=30,samples=11,cases=rows,max_ratio=maximum,qualified=maximum<=1.2,raw_sha256=sha(path),
        method='Quiet same-JVM alternating parent/candidate medians, wall and thread CPU. Native cloud host, not Fold7 device latency.')
    write(REPORTS/'timing.json',result);print(json.dumps(result))


def qualify():
    verify()
    records={name:json.loads((REPORTS/(name+'.json')).read_text()) for name in
             ('native-calibration1450','native-guard3893','learning','android','timing')}
    if not all(r['qualified'] for r in records.values()):raise ValueError('Not every gate passed')
    for fname in ('inference-freeze.json','port-freeze.json','native-freeze.json','guard-wiring-freeze.json'):
        for name,wanted in json.loads((DATA/fname).read_text())['sha256'].items():
            if sha(ROOT/name)!=wanted:raise ValueError('Frozen implementation changed: '+name)
    package='app/src/main/java/hk/cantonesemixeng/keyboard/'
    for name in ('QuickDecoder','TailSupplement','DirectCodeGenerator'):
        if sha(WORK/'candidate'/package/(name+'.java'))!=sha(WORK/'android'/package/(name+'.java')):
            raise ValueError('Android/native inference differs')
    if sha(WORK/'candidate/app/src/main/assets/code_generator.b64')!=sha(WORK/'android/app/src/main/assets/code_generator.b64'):
        raise ValueError('Android/native model differs')
    if list(DATA.glob('reserve-started-*')) or list(REPORTS.glob('independent500*')):raise ValueError('Unused test already started')
    paths=list(Path(__file__).parent.glob('*.py'))+list(Path(__file__).parent.glob('*.java'))
    paths += [DATA/p for p in ('protocol.json','seal.json','code_generator.b64')]
    for stage in ('native','candidate'):
        for folder in ('classes','app/src/main/java','app/src/main/assets'):
            paths += [p for p in sorted((WORK/stage/folder).rglob('*')) if p.is_file()]
    paths += [p for p in sorted((WORK/'android/app/src/main').rglob('*')) if p.is_file()]
    evidence=[p for p in sorted(REPORTS.glob('*')) if p.is_file()]
    write(DATA/'qualification.json',dict(status='All pre-independent gates passed',parent_revision=BASELINE,
        reserve_sha256=sha(ROOT/'tools/data/prefix_language/reserve.tsv'),
        source_model_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},
        gates={k:r['qualified'] for k,r in records.items()},
        policy='One ordinary parent/candidate500 test only. Exact first18 retention; no first/top5/top20 count loss; positive top20 gain. No outcome tuning, APK or1.0 claim.'))
    print('qualified_for_one_independent500=true')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['guards','timing','qualify']);a=p.parse_args()
    {'guards':guards,'timing':timing,'qualify':qualify}[a.mode]()
