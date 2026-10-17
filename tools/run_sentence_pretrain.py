#!/usr/bin/env python3
"""Frozen language-only and language-plus-code adaptation ordinary Java trials."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from native_phrase_relations import build, run, DRIVER
from prepare_sentence_pretrain import DATA, write
from prepare_tatoeba_corpus import digest
from run_context_gru import source as recurrent_source
from run_context_search import assess
from train_phrase_model import ROOT

BASELINE = '1a6a67e'


def check():
    seal = json.loads((DATA/'seal.json').read_text())
    if digest(DATA/'protocol.json') != seal['protocol_sha256']:
        raise ValueError('Sealed protocol changed')
    protocol = json.loads((DATA/'protocol.json').read_text())
    for name, value in {**protocol['source_sha256'], **protocol['evaluation_sha256']}.items():
        if digest(ROOT/name) != value:
            raise ValueError('Frozen sentence experiment source/input changed: ' + name)
    if digest(DATA/'manifest.json') != protocol['manifest_sha256']:
        raise ValueError('Frozen sentence experiment manifest changed')


def source(text):
    return recurrent_source(text).replace('ContextSentenceRanker', 'SentenceLanguageRanker')


def prepare(work, models):
    check()
    if work.exists():
        raise ValueError('Use a fresh ordinary native archive')
    build(work/'baseline', BASELINE, original=True)
    relative = 'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    anchor = 'Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(anchor) != 1:
        raise ValueError('Native constructor changed')
    driver = DRIVER.replace(anchor, anchor[:-2]+',\n   SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))));')
    report = json.loads((models/'report.json').read_text())
    if report['protocol_sha256'] != digest(DATA/'protocol.json'):
        raise ValueError('Fit used a different protocol')
    for arm in ('language', 'adapted'):
        stage = work/arm
        shutil.copytree(work/'baseline', stage)
        (stage/relative).write_text(source((stage/relative).read_text()))
        shutil.copyfile(ROOT/'tools/SentenceLanguageRanker.java', stage/'app/src/main/java/hk/cantonesemixeng/keyboard/SentenceLanguageRanker.java')
        model = models/(arm+'.b64')
        if digest(model) != report['models'][model.name]:
            raise ValueError('Fitted model bytes changed')
        shutil.copyfile(model, stage/'app/src/main/assets/sentence_language.b64')
        (stage/'RelationEvaluation.java').write_text(driver)
        subprocess.run(['javac', '-encoding', 'UTF-8', '-sourcepath', str(stage/'app/src/main/java'),
                        '-d', str(stage/'classes'), str(stage/'RelationEvaluation.java')], check=True)
        null = stage/'SentenceNullEvaluation.java'
        null.write_text(DRIVER.replace('class RelationEvaluation', 'class SentenceNullEvaluation'))
        subprocess.run(['javac', '-encoding', 'UTF-8', '-cp', str(stage/'classes'),
                        '-d', str(stage/'classes'), str(null)], check=True)


def report(results):
    check()
    cases = ROOT/'tools/data/context_search/calibration1450.tsv'
    baseline = ROOT/'tools/reports/context-search-2026-10-16/baseline1450.tsv'
    trials = {arm: assess(cases, baseline, results/(arm+'.tsv'), results/(arm+'.json'))
              for arm in ('language', 'adapted')}
    eligible = [a for a in trials if trials[a]['qualified']]
    selected = max(eligible, key=lambda a: (trials[a]['selection_key'], a == 'language')) if eligible else None
    result = dict(parent_revision=BASELINE, selected=selected, protocol_sha256=digest(DATA/'protocol.json'),
                  trials={a: {k:r[k] for k in ('before','after','new150','old1300','gate','qualified','selection_key')}
                          for a,r in trials.items()}, independent500_decoded=False,
                  decision='Proceed to3893/Single32/Android/quiet timing guards' if selected else
                           'Reject both pretrained arms; retain production and preserve unused context-search500')
    write(DATA/'selection.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('prepare'); a.add_argument('work', type=Path); a.add_argument('models', type=Path)
    a = sub.add_parser('run'); a.add_argument('work', type=Path); a.add_argument('arm', choices=('baseline','language','adapted')); a.add_argument('cases', type=Path); a.add_argument('output', type=Path)
    a = sub.add_parser('report'); a.add_argument('results', type=Path)
    a = p.parse_args()
    if a.mode == 'prepare': prepare(a.work, a.models)
    elif a.mode == 'run': check(); run(a.work/a.arm, a.cases, a.output)
    else: report(a.results)
