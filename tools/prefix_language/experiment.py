"""Fixed-parent native archives for the two authorized prefix-language steps."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from native_phrase_relations import build,DRIVER,run
from prepare_tatoeba_corpus import digest
from prepare_sentence_pretrain import write
from policy import source

BASELINE='28dfb69012ee0e3a94870f0df7d6e11312841ec2'
DATA=ROOT/'tools/data/prefix_language'
REPORTS=ROOT/'tools/reports/prefix-language-2026-10-17'
WORK=ROOT/'.native/prefix-language-20261017'


def driver(search=False):
    value=DRIVER
    if search:value=value.replace('   SentenceRanker.load(', '   QuickDecoder.CLAUSE_START_STRENGTH,\n   SentenceRanker.load(')
    anchor='Files.exists(assets.resolve("relation_ranker.b64"))?PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))):null);'
    suffix=',\n   SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64")))'
    if search:suffix+=',\n   Files.exists(assets.resolve("search_language.b64"))?SearchLanguageRanker.load(Files.newInputStream(assets.resolve("search_language.b64"))):null'
    assert value.count(anchor)==1
    return value.replace(anchor,anchor[:-2]+suffix+');')


def compile_stage(stage):
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),
        '-d',str(stage/'classes'),str(stage/'RelationEvaluation.java')],check=True)


def prepare(stage,checkpoint=None):
    if stage.exists():raise ValueError('Preserve existing native archive')
    build(stage,BASELINE,original=True)
    if checkpoint:
        java=stage/'app/src/main/java/hk/cantonesemixeng/keyboard'
        p=java/'QuickDecoder.java';p.write_text(source(p.read_text()))
        shutil.copyfile(ROOT/'tools/prefix_language/SearchLanguageRanker.java',java/'SearchLanguageRanker.java')
        shutil.copyfile(checkpoint,stage/'app/src/main/assets/search_language.b64')
    (stage/'RelationEvaluation.java').write_text(driver(bool(checkpoint)));compile_stage(stage)


def frozen():
    p=json.loads((DATA/'protocol.json').read_text())
    if digest(DATA/'protocol.json')!=json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Prefix-language protocol changed')
    for name,wanted in {**p['source_sha256'],**p['input_sha256']}.items():
        if digest(ROOT/name)!=wanted:raise ValueError('Frozen prefix-language input changed: '+name)
    return p


def observe(stage):
    from observe_current_search import HOOKS
    prepare(stage)
    p=stage/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java';text=p.read_text()
    def replace(old,new):
        nonlocal text
        if text.count(old)!=1:raise ValueError('Observer anchor changed: '+old)
        text=text.replace(old,new)
    replace('    private static final int BEAM = 48;',HOOKS+'\n    private static final int BEAM = 48;')
    replace('    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {',
        '    private List<Path> currentSearchPrune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {')
    replace('            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);',
        '            observedPosition=pos;\n            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);')
    replace('                if (target.size() > 1024) lattice.set(pos + length,',
        '                if (target.size() > 1024) { observedPosition=pos+length; lattice.set(pos + length,')
    replace('? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));',
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores)); }')
    p.write_text(text)
    value=driver().replace('  int count=0;try(BufferedWriter out=',
        '  int count=0;try(BufferedWriter prefix=Files.newBufferedWriter(Path.of(args[3])); BufferedWriter out=')
    value=value.replace('    List<String> values=q.decode',
        '    QuickDecoder.observedSource=f[0];QuickDecoder.observedContext=f[1];QuickDecoder.observedCode=f[2];QuickDecoder.observedGold=f[3];QuickDecoder.checkpoints.clear();\n    List<String> values=q.decode')
    value=value.replace('    if(++count%100==0)', '    QuickDecoder.writePrefixPairs(prefix);\n    if(++count%100==0)')
    (stage/'RelationEvaluation.java').write_text(value);compile_stage(stage)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['baseline','candidate','observer']);p.add_argument('stage',type=Path);p.add_argument('--checkpoint',type=Path)
    a=p.parse_args()
    if a.mode=='observer':observe(a.stage)
    else:prepare(a.stage,a.checkpoint if a.mode=='candidate' else None)
