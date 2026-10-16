#!/usr/bin/env python3
"""Two fixed final-only recurrent residuals in isolated ordinary Java decoding."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from native_phrase_relations import build,run,DRIVER
from prepare_tatoeba_corpus import digest
from run_context_search import assess
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/context_neural'
CASES=ROOT/'tools/data/context_search/calibration1450.tsv'
RESULTS=ROOT/'tools/reports/context-neural-2026-10-16'
BASELINE='e209474'
ARMS={'half':'context-gru-0.5.b64','full':'context-gru-1.b64'}


def source(text):
    signature='''                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker) throws IOException {'''
    replacement=signature+'''
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, SentenceRanker sentenceRanker,
                        PrefixRanker prefixRanker, PhraseRelationRanker relationRanker, ContextSentenceRanker contextSentenceRanker) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            CLAUSE_START_STRENGTH,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        ContextSentenceRanker contextSentenceRanker) throws IOException {'''
    changes={signature:replacement,
        '    private final SentenceRanker sentenceRanker;':'    private final SentenceRanker sentenceRanker;\n    private final ContextSentenceRanker contextSentenceRanker;',
        '        this.sentenceRanker = sentenceRanker;':'        this.sentenceRanker = sentenceRanker;this.contextSentenceRanker=contextSentenceRanker;',
        'scores.put(path.text, path.score + sentenceRanker.score(context, path.text));':
            'scores.put(path.text, path.score + sentenceRanker.score(context, path.text)\n                    + (contextSentenceRanker==null?0:contextSentenceRanker.score(context,path.text)));'}
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Recurrent integration anchor changed: '+old)
        text=text.replace(old,new)
    return text


def check():
    p=json.loads((DATA/'protocol.json').read_text())
    for name,value in {**p['source_sha256'],**p['input_sha256']}.items():
        if digest(ROOT/name)!=value:raise ValueError('Frozen recurrent input/source changed: '+name)
    return p


def prepare(work,models):
    check()
    if work.exists():raise ValueError('Use a fresh native recurrent archive')
    build(work/'baseline',BASELINE,original=True)
    relative='app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    footer='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(footer)!=1:raise ValueError('Native recurrent constructor anchor changed')
    driver=DRIVER.replace(footer,footer[:-2]+',\n   ContextSentenceRanker.load(Files.newInputStream(assets.resolve("context_gru.b64"))));')
    fitted=json.loads((models/'report.json').read_text())
    for arm,name in ARMS.items():
        target=work/arm;shutil.copytree(work/'baseline',target)
        (target/relative).write_text(source((target/relative).read_text()))
        shutil.copyfile(ROOT/'tools/ContextSentenceRanker.java',target/'app/src/main/java/hk/cantonesemixeng/keyboard/ContextSentenceRanker.java')
        if digest(models/name)!=fitted['models'][name]:raise ValueError('Fitted recurrent bytes changed')
        shutil.copyfile(models/name,target/'app/src/main/assets/context_gru.b64')
        (target/'RelationEvaluation.java').write_text(driver)
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(target/'app/src/main/java'),'-d',str(target/'classes'),str(target/'RelationEvaluation.java')],check=True)
        # Also compile the unextended original driver to verify explicit null parity.
        (target/'RecurrentNullEvaluation.java').write_text(DRIVER.replace('class RelationEvaluation','class RecurrentNullEvaluation'))
        subprocess.run(['javac','-encoding','UTF-8','-cp',str(target/'classes'),'-d',str(target/'classes'),str(target/'RecurrentNullEvaluation.java')],check=True)


def report(results):
    check();scores={}
    before=ROOT/'tools/reports/context-search-2026-10-16/baseline1450.tsv'
    for arm in ARMS:scores[arm]=assess(CASES,before,results/(arm+'.tsv'),results/(arm+'.json'))
    eligible=[a for a in ARMS if scores[a]['qualified']]
    selected=max(eligible,key=lambda a:(scores[a]['selection_key'],a=='half')) if eligible else None
    value=dict(selected=selected,protocol_sha256=digest(DATA/'protocol.json'),fresh500_decoded=False,
        trials={a:{k:scores[a][k] for k in ('before','after','new150','old1300','gate','qualified','selection_key')} for a in ARMS},
        decision='Proceed to guarded qualification' if selected else 'Reject both recurrent residual strengths; retain original app and leave fresh500 untested')
    (DATA/'selection.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(json.dumps(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    a=s.add_parser('prepare');a.add_argument('work',type=Path);a.add_argument('models',type=Path)
    a=s.add_parser('run');a.add_argument('work',type=Path);a.add_argument('arm',choices=('baseline',*ARMS));a.add_argument('cases',type=Path);a.add_argument('output',type=Path)
    a=s.add_parser('report');a.add_argument('results',type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.work,a.models)
    elif a.mode=='run':check();run(a.work/a.arm,a.cases,a.output)
    else:report(a.results)
