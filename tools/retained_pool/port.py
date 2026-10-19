"""Port the fixed pool fusion into an isolated copy of the actual Android code."""
import base64
import gzip
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
from study import ROOT,HERE,DATA,WORK,REPORTS,CHECKPOINT,CODES,KNOWN,sha,write,verify_inference
from model import NAMES,load,Codec,decode


def replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Port anchor changed: '+old[:100])
    return text.replace(old,new)


def quick(text):
    text=replace(text,'    private final DirectCodeGenerator codeGenerator;',
        '    private final DirectCodeGenerator codeGenerator, expandedGenerator;\n    private final Set<Integer> addedCharacters;')
    # Keep every old constructor binary/source path delegating to the same
    # implementation with expansion absent, including clause-strength tests.
    anchor='''        this.codeGenerator=codeGenerator;
        if (!Double.isFinite(clauseStartStrength)'''
    prefix='''        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,codeGenerator,null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, SentenceRanker sentenceRanker,
                        PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        SentenceLanguageRanker contextSentenceRanker, DirectCodeGenerator codeGenerator,
                        DirectCodeGenerator expandedGenerator) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            CLAUSE_START_STRENGTH,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,codeGenerator,expandedGenerator);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        SentenceLanguageRanker contextSentenceRanker, DirectCodeGenerator codeGenerator,
                        DirectCodeGenerator expandedGenerator) throws IOException {
        this.codeGenerator=codeGenerator;this.expandedGenerator=expandedGenerator;
        this.addedCharacters=expandedGenerator==null ? Collections.emptySet()
            : expandedGenerator.charactersAddedSince(codeGenerator);
        if (!Double.isFinite(clauseStartStrength)'''
    text=replace(text,anchor,prefix)
    text=replace(text,'        return TailSupplement.apply(visible,proposed,',
        '        List<String> deployed=TailSupplement.apply(visible,proposed,')
    anchor='''                +relationRanker.alignedCorrection(relationRanker.rawScore(context,text),reference),false);
    }

    /** Whole-word decisions'''
    text=replace(text,anchor,'''                +relationRanker.alignedCorrection(relationRanker.rawScore(context,text),reference),false);
        // The full deployed pool, including its old generated choices, reaches
        // this stage unchanged. Expansion can offer only new-character strings.
        if(expandedGenerator==null || addedCharacters.isEmpty() || Thread.currentThread().isInterrupted()) return deployed;
        List<String> expanded=NewCharacterSupplement.filter(expandedGenerator.generate(code,context),addedCharacters);
        if(visiblePersonalPreference(code,context,expanded,learned,contextual)) return deployed;
        for(String text:expanded) if(learnedSequence(code,text,learned)) return deployed;
        return TailSupplement.apply(deployed,expanded,
            text -> !dictionary.matchQuickCodes(code,text).isEmpty(),
            text -> languageScore(context,text)+sentenceRanker.score(context,text)
                +relationRanker.alignedCorrection(relationRanker.rawScore(context,text),reference),false);
    }

    /** Whole-word decisions''')
    return text


def generator(text):
    text=replace(text,'private static final int H = 32, C = 16, V = 2251, BEAM = 24;',
        'private static final int H = 32, C = 16, BEAM = 24;')
    text=replace(text,'''            if(in.readInt()!=0x44434731 || in.readInt()!=32 || in.readInt()!=32 || in.readInt()!=16
                    || in.readInt()!=V || in.readInt()!=12 || in.readInt()!=48 || in.readInt()!=BEAM)
                throw new IOException("Invalid direct-code model header");''',
        '''            if(in.readInt()!=0x44434731 || in.readInt()!=32 || in.readInt()!=32 || in.readInt()!=16)
                throw new IOException("Invalid direct-code model header");
            int V=in.readInt();
            // Only the two qualified schema sizes are accepted, before any
            // allocation. Existing models and their search math stay identical.
            if((V!=2251 && V!=2496) || in.readInt()!=12 || in.readInt()!=48 || in.readInt()!=BEAM)
                throw new IOException("Invalid direct-code model header");''')
    anchor='    private int id(int cp)'
    text=replace(text,anchor,'''    Set<Integer> charactersAddedSince(DirectCodeGenerator baseline) {
        if(baseline==null) return Collections.emptySet();
        Set<Integer> additions=new HashSet<>();
        for(int cp:characters) additions.add(cp);
        for(int cp:baseline.characters) if(!additions.remove(cp)) return Collections.emptySet();
        return Collections.unmodifiableSet(additions);
    }
    private int id(int cp)''')
    return text


def service(text):
    anchor='                QuickDecoder phrases = new QuickDecoder('
    text=replace(text,anchor,'''                DirectCodeGenerator expandedGenerator;
                try {
                    expandedGenerator = DirectCodeGenerator.load(getAssets().open("expanded_generator.b64"));
                } catch (IOException optionalModelUnavailable) {
                    expandedGenerator = null;
                }
'''+anchor)
    return replace(text,'relationRanker, sentenceLanguageRanker, codeGenerator);',
        'relationRanker, sentenceLanguageRanker, codeGenerator, expandedGenerator);')


def prepare():
    verify_inference()
    if not all(json.loads((REPORTS/(n+'.json')).read_text())['qualified'] for n in KNOWN):
        raise ValueError('Known gates failed')
    stage=WORK/'candidate'
    if stage.exists():raise ValueError('Preserve existing port')
    shutil.copytree(WORK/'native',stage);shutil.rmtree(stage/'classes')
    java=stage/'app/src/main/java/hk/cantonesemixeng/keyboard'
    for name,change in [('QuickDecoder',quick),('DirectCodeGenerator',generator),('CantoneseMixEngKeyboardService',service)]:
        path=java/(name+'.java');path.write_text(change(path.read_text()))
    shutil.copyfile(HERE/'NewCharacterSupplement.java',java/'NewCharacterSupplement.java')
    v,chars=load(CHECKPOINT);codes=json.loads(CODES.read_text())
    raw=io.BytesIO();raw.write(struct.pack('>8i',0x44434731,32,32,16,len(chars)+3,12,48,24))
    for char in chars:
        choices=codes[char];raw.write(struct.pack('>iB',ord(char),len(choices)))
        for code in choices:
            b=code.encode('ascii');raw.write(struct.pack('>H',len(b))+b)
    for key in NAMES:raw.write(v[key].astype('>f4').tobytes())
    output=DATA/'expanded_generator.b64'
    with output.open('xb') as out:out.write(base64.b64encode(gzip.compress(raw.getvalue(),mtime=0))+b'\n')
    shutil.copyfile(output,stage/'app/src/main/assets/expanded_generator.b64')
    sources=[ROOT/'tools/tail_supplement/GeneratorCheck.java',HERE/'FusionIntegratedEvaluation.java']
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),
        '-d',str(stage/'classes')]+list(map(str,sources)),check=True)
    paths=[Path(__file__),output]+sources+sorted(java.glob('*.java'))
    write(DATA/'port-freeze.json',dict(checkpoint_sha256=sha(CHECKPOINT),model_sha256=sha(output),
        original_asset_unchanged=sha(stage/'app/src/main/assets/code_generator.b64')==sha(ROOT/'app/src/main/assets/code_generator.b64'),
        primitive_weight_bytes=sum(a.nbytes for a in v.values()),
        sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}))
    print('Exact fixed dual-provider pipeline staged; no production edits')


def check():
    verify_inference()
    for name,wanted in json.loads((DATA/'port-freeze.json').read_text())['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Frozen port changed: '+name)


def parity():
    check();stage=WORK/'candidate';bad=WORK/'corrupt';bad.mkdir()
    raw=gzip.decompress(base64.b64decode((DATA/'expanded_generator.b64').read_bytes()))
    samples=[]
    for i in range(8):
        modified=bytearray(raw);modified[4*i:4*i+4]=struct.pack('>i',-1);samples.append(bytes(modified))
    samples += [raw[:-1],raw+b'X',b'bad',raw[:40]]
    for count in (0,2252,2497,2**30):
        modified=bytearray(raw);modified[16:20]=struct.pack('>i',count);samples.append(bytes(modified))
    modified=bytearray(raw);modified[32:36]=struct.pack('>i',0);samples.append(bytes(modified))
    at=32
    for _ in range(2493):
        count=raw[at+4];at+=5
        for _ in range(count):length=struct.unpack('>H',raw[at:at+2])[0];at+=2+length
    for value in (float('nan'),float('inf'),65.):
        modified=bytearray(raw);modified[at:at+4]=struct.pack('>f',value);samples.append(bytes(modified))
    for i,sample in enumerate(samples):
        (bad/f'{i:02}.b64').write_bytes(base64.b64encode(gzip.compress(sample,mtime=0)))
    rows=(ROOT/'tools/data/prefix_language/observation-cases.tsv').read_text().splitlines()[:80]
    pairs=[(f[1],f[2]) for f in (r.split('\t') for r in rows)]
    pairs += [('English😀你今日','OFONAOVRMRQ'),('你今日😀','a'),('','zz'),('','123'),('','a'*49)]
    with (REPORTS/'generator-parity.txt').open('x') as out:
        for label,checkpoint,codes,asset in [
                ('expanded',CHECKPOINT,CODES,'expanded_generator.b64'),
                ('legacy',ROOT/'tools/data/code_generator/models/teacher.npz',ROOT/'tools/data/code_generator/codes.json','code_generator.b64')]:
            v,chars=load(checkpoint);codec=Codec(chars,json.loads(codes.read_text()))
            path=WORK/(label+'-parity.tsv')
            with path.open('x') as data:
                for context,code in pairs:
                    items=decode(v,codec,code,context)
                    data.write('\t'.join([context,code,'|'.join(t for t,s in items),'|'.join(repr(s) for t,s in items)])+'\n')
            result=subprocess.check_output(['java','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.GeneratorCheck',
                str(stage/'app/src/main/assets'/asset),str(path),str(bad)],text=True)
            out.write(label+' '+result);print(label,result.strip())
    inputs=[]
    for name in KNOWN:
        inputs += (WORK/(name+'-inputs.tsv')).read_text().splitlines()
    for part in range(4):
        (WORK/f'full-inputs-{part}.tsv').write_text(''.join(s+'\n' for s in inputs[part::4]))
    paths=[p for p in sorted((stage/'classes').rglob('*')) if p.is_file()]
    paths += [stage/'app/src/main/assets/expanded_generator.b64',Path(__file__)]
    write(DATA/'native-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        ordered_score_comparisons=170,corrupt_checks_each=len(samples),before_full_native_known=True))


def run(part):
    check()
    for name,wanted in json.loads((DATA/'native-freeze.json').read_text())['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Frozen native changed: '+name)
    stage=WORK/'candidate';output=WORK/f'full-output-{part}.tsv'
    if output.exists():raise ValueError('Preserve ordinary native outputs')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.FusionIntegratedEvaluation',
        str(stage/'app/src/main/assets'),str(WORK/f'full-inputs-{part}.tsv'),str(output),'candidate'],check=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','parity','run']);p.add_argument('--part',type=int,choices=range(4));a=p.parse_args()
    if a.mode=='run':
        if a.part is None:p.error('--part required')
        run(a.part)
    else:{'prepare':prepare,'parity':parity}[a.mode]()
