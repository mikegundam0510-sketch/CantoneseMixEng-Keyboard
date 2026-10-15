#!/usr/bin/env python3
"""Shared-score search/final trial in an archived tree, without touching the app."""
import argparse
from pathlib import Path
import shutil
import subprocess
from native_phrase_relations import build,run,DRIVER
from prepare_joint_ranking import BASELINE
from train_phrase_model import ROOT

def empty_archive(work):
    work=work.resolve()
    if work==ROOT or ROOT.is_relative_to(work):raise ValueError('Choose an archive directory outside the checkout root')
    if work.exists() and any(work.iterdir()):raise ValueError('Choose a new or empty archive directory; existing files are preserved')
    return work

def source(text,mode='joint'):
    signature='''                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker) throws IOException {'''
    replacement=signature+'''
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, SentenceRanker sentenceRanker,
                        PrefixRanker prefixRanker, PhraseRelationRanker relationRanker, CandidateRanker jointRanker) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            CLAUSE_START_STRENGTH,sentenceRanker,prefixRanker,relationRanker,jointRanker);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        CandidateRanker jointRanker) throws IOException {'''
    changes={signature:replacement,
        '    private final CandidateRanker candidateRanker;':'    private final CandidateRanker candidateRanker, jointRanker;',
        '        this.candidateRanker = candidateRanker;':'        this.candidateRanker = candidateRanker; this.jointRanker=jointRanker;'}
    if mode=='joint':
        changes['            + (candidateRanker == null ? 0 : candidateRanker.score(prefix, text))']=\
            '            + (candidateRanker == null ? 0 : candidateRanker.score(prefix, text))\n            + (jointRanker == null ? 0 : jointRanker.score(prefix, text))'
    elif mode=='final':
        changes['scores.put(path.text, path.score + sentenceRanker.score(context, path.text));']=\
            'scores.put(path.text, path.score + sentenceRanker.score(context, path.text)\n                    + (jointRanker==null?0:jointRanker.score(context,path.text)));'
    else:raise ValueError('Unknown joint-scoring mode')
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Shared score hook changed: '+old)
        text=text.replace(old,new)
    return text

def prepare(work,model,mode='joint'):
    work=empty_archive(work)
    build(work,BASELINE,original=True)
    quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java';quick.write_text(source(quick.read_text(),mode))
    shutil.copyfile(model,work/'app/src/main/assets/joint_ranker.b64')
    old='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    if DRIVER.count(old)!=1:raise ValueError('Native constructor hook changed')
    driver=DRIVER.replace(old,old[:-2]+',\n   CandidateRanker.load(Files.newInputStream(assets.resolve("joint_ranker.b64"))));')
    java=work/'RelationEvaluation.java';java.write_text(driver)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','run'));p.add_argument('work',type=Path)
    p.add_argument('--model',type=Path);p.add_argument('--policy',choices=('joint','final'),default='joint')
    p.add_argument('--cases',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.mode=='prepare':
        if a.model is None:p.error('prepare requires --model')
        prepare(a.work,a.model,a.policy)
    elif a.cases is None or a.output is None:p.error('run requires --cases and --output')
    else:run(a.work,a.cases,a.output)
