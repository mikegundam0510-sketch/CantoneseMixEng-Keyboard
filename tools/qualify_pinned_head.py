#!/usr/bin/env python3
"""Freeze an exactly verified candidate before the sole independent comparison."""
import argparse
import json
from pathlib import Path
from prepare_tatoeba_corpus import digest
from run_pinned_head import DATA,REPORTS,ROOT,check,freeze_check


def qualify(native,android):
    protocol=check();freeze_check(native)
    records={name:json.loads((REPORTS/(name+'.json')).read_text()) for name in ('calibration1450','guard3893','single32','android','timing')}
    if not all(r['qualified'] for r in records.values()):raise ValueError('Not every pre-independent guard passed')
    for name in ('calibration1450','guard3893'):
        if not records[name]['coverage']['all_original_first_choices_identical']:
            raise ValueError('Original first choices not preserved')
    if records['single32']['contextual']!=[32,32,32]:raise ValueError('Single32 failed')
    unit=records['android']['unit_tests'];lint=records['android']['lint']
    if unit['tests']!=222 or any(unit[k] for k in ('failures','errors','skipped')) or any(lint.get(k,0) for k in ('Error','Fatal')):
        raise ValueError('Android checks failed')
    timing=records['timing']
    if timing['warmup']!=30 or timing['samples']!=11 or len(timing['cases'])!=6 or timing['max_ratio']>1.2:
        raise ValueError('Quiet timing failed')
    package='app/src/main/java/hk/cantonesemixeng/keyboard/'
    for name in ('QuickDecoder','SentenceLanguageRanker','VisibleCandidateReranker','PinnedHeadReranker','CandidateEngine','EnglishChineseEngine'):
        if digest(native/'candidate'/package/(name+'.java'))!=digest(android/package/(name+'.java')):
            raise ValueError('Android/native source mismatch: '+name)
    if digest(native/'candidate/app/src/main/assets/sentence_language.b64')!=digest(android/'app/src/main/assets/sentence_language.b64'):
        raise ValueError('Wired language model mismatch')
    if list(DATA.glob('reserve-started-*')) or list(REPORTS.glob('independent500*')):
        raise ValueError('Reserve already started')
    source=list(protocol['source_sha256'])+[str(p.relative_to(ROOT)) for p in (DATA/'protocol.json',DATA/'seal.json',DATA/'inference-freeze.json',Path(__file__).resolve())]
    source += [str(p.relative_to(ROOT)) for p in sorted((android/'app/src/main').rglob('*')) if p.is_file()]
    evidence=[p for p in sorted(REPORTS.glob('*')) if p.is_file()]
    value=dict(status='All pre-independent guards passed',selected='candidate',baseline_revision=protocol['parent_revision'],
        protocol_sha256=digest(DATA/'protocol.json'),independent500_sha256=protocol['input_sha256']['tools/data/context_search/heldout.tsv'],
        reserve_runner_sha256=digest(ROOT/'tools/evaluate_pinned_head_reserve.py'),
        source_sha256={p:digest(ROOT/p) for p in source},evidence_sha256={str(p.relative_to(ROOT)):digest(p) for p in evidence},
        native_file_sha256={arm:{str(p.relative_to(native/arm)):digest(p) for folder in ('classes','app/src/main/java','app/src/main/assets') for p in sorted((native/arm/folder).rglob('*')) if p.is_file()} for arm in ('baseline','candidate')},
        gates={name:{k:r[k] for k in ('qualified',)} for name,r in records.items()},
        policy='One ordinary parent/candidate reserve pass, strict first/set preservation and positive top5 gain. No outcome-based tuning, APK or1.0 claim.')
    with (DATA/'qualification.json').open('x') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print('qualified_for_one_independent500_comparison=true')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native',type=Path);p.add_argument('android',type=Path)
    a=p.parse_args();qualify(a.native.resolve(),a.android.resolve())
