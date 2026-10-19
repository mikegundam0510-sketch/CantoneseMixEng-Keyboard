"""Qualify full native outputs, stage exact Android and unchanged learning checks."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from study import ROOT,HERE,DATA,WORK,REPORTS,KNOWN,BASELINE,sha,write,verify_inference
from port import replace,check


def report():
    check();total=sum(len(p[0].read_text().splitlines()) for p in KNOWN.values());rows=[None]*total
    for part in range(4):
        values=(WORK/f'full-output-{part}.tsv').read_text().splitlines()
        if len(values)!=len(rows[part::4]):raise ValueError('Partial native results')
        rows[part::4]=values
    expected=[]
    for name in KNOWN:expected+=(WORK/(name+'-predictions.tsv')).read_text().splitlines()
    if rows!=expected:raise ValueError('Actual Java pipeline differs from frozen screening')
    write(REPORTS/'native-known.json',dict(qualified=True,ordinary_full_cases=total,
        all_ordered_displays_identical_to_screening=True,targets_absent_from_inputs=True,
        actual_legacy_provider_active=True,deployed_first18_identical=True,exact_codes=True,
        max20_unique=True,maximum_new2=True,new_characters_only=True))
    print('Full native5343 lists exactly reproduce fixed screening')


def prepare():
    check();stage=WORK/'candidate';classes=stage/'classes'
    if not all(json.loads((REPORTS/(n+'.json')).read_text())['qualified'] for n in KNOWN):
        raise ValueError('Known screening gates failed')
    source=(ROOT/'tools/ContextLearningEvaluation.java').read_text()
    start=source.index('        QuickDecoder decoder=new QuickDecoder(')
    end=source.index('\n        List<String[]> cases=',start)
    source=source[:start]+'''        FusionIntegratedEvaluation.assets=assets;
        QuickDecoder decoder=FusionIntegratedEvaluation.decoder(dictionary,true);
        QuickDecoder baseline=FusionIntegratedEvaluation.decoder(dictionary,false);'''+source[end:]
    for name,call in [('old','baseline.decode(fields[1],learned,fields[0])'),
                      ('updated','baseline.decode(fields[1],learned,fields[0],preferences)')]:
        anchor='                List<String> '+name+'=decoder.decode(fields[1],learned,fields[0]'+(');' if name=='old' else ',preferences);')
        source=replace(source,anchor,anchor+'\n                if(!'+name+'.equals('+call+')) throw new AssertionError("Single learned display differs from deployed parent");')
    path=stage/'ContextLearningEvaluation.java';path.write_text(source)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-cp',str(classes),
        '-d',str(classes),str(path),str(HERE/'FusionProtectionCheck.java')],check=True)
    perf=(ROOT/'tools/PairedRankingPerformance.java').read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    perf=replace(perf,anchor,'''            Class<?> slm=classes.loadClass(pkg+"SentenceLanguageRanker");types.add(slm);
            values.add(slm.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("sentence_language.b64"))));
            Class<?> gen=classes.loadClass(pkg+"DirectCodeGenerator");types.add(gen);
            values.add(gen.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("code_generator.b64"))));
            if(Files.exists(assets.resolve("expanded_generator.b64"))) {
                types.add(gen);
                values.add(gen.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("expanded_generator.b64"))));
            }
'''+anchor)
    path=WORK/'PairedRankingPerformance.java';path.write_text(perf)
    subprocess.run(['javac','-encoding','UTF-8','-d',str(WORK/'performance-classes'),str(path)],check=True)
    # Select first four changed displays by code/context and full lists alone.
    rows=(WORK/'calibration1450-inputs.tsv').read_text().splitlines()
    predictions=(WORK/'calibration1450-predictions.tsv').read_text().splitlines();selected=[]
    for before,after in zip(rows,predictions):
        if before.split('\t')[3]!=after.split('\t')[3]:selected.append(before)
        if len(selected)==4:break
    if len(selected)!=4:raise ValueError('Need four active target-free fixtures')
    (WORK/'protection-inputs.tsv').write_text(''.join(s+'\n' for s in selected))
    android=WORK/'android'
    if android.exists():raise ValueError('Preserve existing Android stage')
    android.mkdir()
    blob=subprocess.check_output(['git','archive',BASELINE],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:archive.extractall(android,filter='data')
    package=Path('app/src/main/java/hk/cantonesemixeng/keyboard')
    for name in ('QuickDecoder','DirectCodeGenerator','NewCharacterSupplement','CantoneseMixEngKeyboardService'):
        shutil.copyfile(stage/package/(name+'.java'),android/package/(name+'.java'))
    shutil.copyfile(DATA/'expanded_generator.b64',android/'app/src/main/assets/expanded_generator.b64')
    shutil.copyfile(ROOT/'app/src/main/assets/stroke.tsv',android/'app/src/main/assets/stroke.tsv')
    shutil.copytree(ROOT/'app/src/main/assets/licenses/stroke',android/'app/src/main/assets/licenses/stroke')
    paths=[Path(__file__),HERE/'FusionProtectionCheck.java',stage/'ContextLearningEvaluation.java',
        WORK/'PairedRankingPerformance.java',WORK/'protection-inputs.tsv',ROOT/'tools/hk_daily_context_cases.tsv']
    paths += sorted(p for p in (android/'app/src/main').rglob('*') if p.is_file())
    write(DATA/'guard-wiring-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        actual_current_parent_includes_old_generator=True,android_service_loads_optional_expansion=True))
    print('Learning, fallback, quiet paired timing and exact Android candidate staged')


def learning():
    check();stage=WORK/'candidate'
    runs=[('FusionProtectionCheck',[str(stage/'app/src/main/assets'),str(WORK/'protection-inputs.tsv')],'protection.txt'),
        ('ContextLearningEvaluation',[str(stage/'app/src/main/assets'),str(ROOT/'tools/hk_daily_context_cases.tsv'),str(REPORTS/'single32.tsv')],'single32.txt')]
    for name,args,filename in runs:
        result=subprocess.check_output(['java','-Xmx2g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.'+name]+args,text=True)
        with (REPORTS/filename).open('x') as out:out.write(result)
        print(result.strip())
    if 'cases=32 sequence_records=489 legacy=[30, 32, 32] contextual=[32, 32, 32]' not in (REPORTS/'single32.txt').read_text():
        raise ValueError('Single learning failed')
    write(REPORTS/'learning.json',dict(qualified=True,single_cases=32,sequence_records=489,
        repetitions=3,legacy=[30,32,32],contextual=[32,32,32],all_learned_displays_identical_to_deployed=True,
        active_protection_cases=4,optional_no_additions_no_legacy_personal_mixed_translation=True))


def android():
    directory=WORK/'android';tests=Counter()
    paths=list((directory/'app/build/test-results/testDebugUnitTest').glob('TEST-*.xml'))
    if not paths:raise ValueError('Android unit results missing')
    for path in paths:
        node=ET.parse(path).getroot()
        for key in ('tests','failures','errors','skipped'):tests[key]+=int(node.get(key,0))
    if tests['tests']!=222 or any(tests[k] for k in ('failures','errors','skipped')):raise ValueError('Android unit failures/partial')
    lint=Counter(n.get('severity') for n in ET.parse(directory/'app/build/reports/lint-results-debug.xml').getroot().findall('issue'))
    if lint['Error'] or lint['Fatal']:raise ValueError('Android lint errors')
    if 'BUILD SUCCESSFUL' not in (WORK/'android-checks.log').read_text():raise ValueError('Build not complete')
    if list(directory.rglob('*.apk')):raise ValueError('No APK authorized')
    write(REPORTS/'android.json',dict(qualified=True,unit_tests=dict(tests),lint=dict(lint),apk_produced=False,
        wiring='Actual optional expansion loader and constructor, exact native inference sources and assets'))
    print('Android units',dict(tests),'Lint',dict(lint),'no APK')


def timing():
    raw=REPORTS/'timing.tsv';rows=[]
    if '# warmup=30 samples=11' not in raw.read_text():raise ValueError('Timing incomplete')
    for line in raw.read_text().splitlines():
        if not line or line.startswith('#'):continue
        f=line.split('\t');bw,aw,bc,ac=map(float,f[2:])
        rows.append(dict(code=f[0],letters=int(f[1]),before_wall_ms=bw,after_wall_ms=aw,
            before_cpu_ms=bc,after_cpu_ms=ac,wall_ratio=aw/bw,cpu_ratio=ac/bc))
    if len(rows)!=6:raise ValueError('Timing incomplete')
    maximum=max(max(r['wall_ratio'],r['cpu_ratio']) for r in rows)
    write(REPORTS/'timing.json',dict(qualified=maximum<=1.2,cases=rows,max_ratio=maximum,
        warmup=30,samples=11,method='Quiet same-JVM alternating actual deployed/candidate; cloud wall and thread CPU, not Fold7/startup latency',raw_sha256=sha(raw)))
    print('timing maximum ratio',maximum,'qualified',maximum<=1.2)


def qualify():
    check()
    names=['calibration1450','guard3893','native-known','learning','android','timing']
    if not all(json.loads((REPORTS/(n+'.json')).read_text())['qualified'] for n in names):
        raise ValueError('Pre-independent gate failed')
    for name in ('inference-freeze.json','port-freeze.json','native-freeze.json','guard-wiring-freeze.json'):
        for path,wanted in json.loads((DATA/name).read_text())['sha256'].items():
            if sha(ROOT/path)!=wanted:raise ValueError('Qualification freeze changed: '+path)
    for relative in ['app/src/main/java/hk/cantonesemixeng/keyboard/'+n+'.java' for n in
            ('QuickDecoder','DirectCodeGenerator','NewCharacterSupplement','CantoneseMixEngKeyboardService')]+['app/src/main/assets/expanded_generator.b64']:
        if sha(WORK/'candidate'/relative)!=sha(WORK/'android'/relative):raise ValueError('Android/native wiring differs')
    if (DATA/'reserve-started.json').exists():raise ValueError('Reserve already started')
    paths=list(HERE.glob('*.py'))+list(HERE.glob('*.java'))
    for stage in ('native','candidate'):
        for folder in ('classes','app/src/main/java','app/src/main/assets'):
            paths+=sorted(p for p in (WORK/stage/folder).rglob('*') if p.is_file())
    paths+=sorted(p for p in (WORK/'android/app/src/main').rglob('*') if p.is_file())
    write(DATA/'qualification.json',dict(status='All known/native/learning/Android/timing gates passed',
        parent_revision=BASELINE,source_model_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in REPORTS.glob('*') if p.is_file()},
        reserve_sha256=sha(ROOT/'tools/data/vocabulary_expansion/reserve.tsv'),
        rule='Once each actual current-parent/candidate500, first18 exact, no first/top5/top20 count loss and positive top20 gain; no independent-based tuning. No APK.'))
    print('Qualified for one unused500 comparison')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['report','prepare','learning','android','timing','qualify']);a=p.parse_args()
    globals()[a.mode]()
