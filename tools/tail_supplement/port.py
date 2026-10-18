"""Export the frozen teacher checkpoint and stage optional production wiring."""
import argparse
import base64
import gzip
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
from study import ROOT, DATA, WORK, REPORTS, BASELINE, verify, write, sha
sys.path.insert(0, str(ROOT / 'tools/code_generator'))
from model import load, NAMES


def quick_source(text):
    anchor = '    private final SentenceLanguageRanker contextSentenceRanker;'
    if text.count(anchor) != 1: raise ValueError('Generator field anchor changed')
    text = text.replace(anchor, anchor+'\n    private final DirectCodeGenerator codeGenerator;')
    anchor = '''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        if (!Double.isFinite(clauseStartStrength)'''
    if text.count(anchor) != 1: raise ValueError('Generator constructor anchor changed')
    text = text.replace(anchor, '''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, SentenceRanker sentenceRanker,
                        PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        SentenceLanguageRanker contextSentenceRanker, DirectCodeGenerator codeGenerator) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            CLAUSE_START_STRENGTH,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,codeGenerator);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        SentenceLanguageRanker contextSentenceRanker, DirectCodeGenerator codeGenerator) throws IOException {
        this.codeGenerator=codeGenerator;
        if (!Double.isFinite(clauseStartStrength)''')
    anchor = '''        return PinnedHeadReranker.rerank(result,finalScores,
            text -> contextSentenceRanker.score(context,text));'''
    if text.count(anchor) != 1: raise ValueError('Generator post-display anchor changed')
    text = text.replace(anchor, '''        List<String> visible=PinnedHeadReranker.rerank(result,finalScores,
            text -> contextSentenceRanker.score(context,text));
        if(codeGenerator==null || relationRanker==null || !relationRanker.aligned() || visible.size()<5) return visible;
        for(String text:visible) if(learnedSequence(code,text,learned)) return visible;
        List<String> proposed=codeGenerator.generate(code,context);
        if(visiblePersonalPreference(code,context,proposed,learned,contextual)) return visible;
        for(String text:proposed) if(learnedSequence(code,text,learned)) return visible;
        double reference=relationRanker.rawScore(context,visible.get(0));
        return TailSupplement.apply(visible,proposed,
            text -> !dictionary.matchQuickCodes(code,text).isEmpty(),
            text -> languageScore(context,text)+sentenceRanker.score(context,text)
                +relationRanker.alignedCorrection(relationRanker.rawScore(context,text),reference),false);''')
    return text


def service_source(text):
    anchor = '                QuickDecoder phrases = new QuickDecoder('
    if text.count(anchor) != 1: raise ValueError('Service generator loader changed')
    text = text.replace(anchor, '''                DirectCodeGenerator codeGenerator;
                try {
                    codeGenerator = DirectCodeGenerator.load(getAssets().open("code_generator.b64"));
                } catch (IOException optionalModelUnavailable) {
                    codeGenerator = null;
                }
'''+anchor)
    anchor = 'candidateRanker, wordRanker, sentenceRanker, prefixRanker, relationRanker, sentenceLanguageRanker);'
    if text.count(anchor) != 1: raise ValueError('Service generator constructor changed')
    return text.replace(anchor,anchor[:-2]+', codeGenerator);')


def prepare():
    verify()
    if not json.loads((REPORTS/'guard3893.json').read_text())['qualified']:
        raise ValueError('Regression guard failed')
    output = DATA/'code_generator.b64'
    if output.exists() or (WORK/'candidate').exists(): raise ValueError('Preserve completed port')
    values, chars=load(ROOT/'tools/data/code_generator/models/teacher.npz')
    codes=json.loads((ROOT/'tools/data/code_generator/codes.json').read_text())
    raw=io.BytesIO();raw.write(struct.pack('>8i',0x44434731,32,32,16,len(chars)+3,12,48,24))
    for char in chars:
        choices=codes[char];raw.write(struct.pack('>iB',ord(char),len(choices)))
        for code in choices:
            b=code.encode('ascii');raw.write(struct.pack('>H',len(b))+b)
    for name in NAMES: raw.write(values[name].astype('>f4').tobytes())
    with output.open('xb') as out: out.write(base64.b64encode(gzip.compress(raw.getvalue(),mtime=0))+b'\n')
    stage=WORK/'candidate';shutil.copytree(WORK/'native',stage)
    shutil.rmtree(stage/'classes')
    java=stage/'app/src/main/java/hk/cantonesemixeng/keyboard'
    path=java/'QuickDecoder.java';path.write_text(quick_source(path.read_text()))
    for name in ('TailSupplement.java','DirectCodeGenerator.java'):
        shutil.copyfile(Path(__file__).parent/name,java/name)
    shutil.copyfile(output,stage/'app/src/main/assets/code_generator.b64')
    write(DATA/'port-freeze.json',dict(checkpoint_sha256=sha(ROOT/'tools/data/code_generator/models/teacher.npz'),
        model_sha256=sha(output), primitive_weight_bytes=sum(a.nbytes for a in values.values()),
        sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),Path(__file__).parent/'DirectCodeGenerator.java',
            java/'QuickDecoder.java',java/'TailSupplement.java',java/'DirectCodeGenerator.java',output]}))
    print('exported frozen teacher; staged native generator; no production changes')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['prepare'])
    parser.parse_args();prepare()
