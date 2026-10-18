"""Stage unchanged learning/performance harnesses and exact Android candidate."""
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
from study import ROOT,DATA,WORK,REPORTS,BASELINE,verify,write,sha
from port import service_source


def main():
    verify();stage=WORK/'candidate';classes=stage/'classes';folder=Path(__file__).parent
    source=(ROOT/'tools/ContextLearningEvaluation.java').read_text()
    anchor='? PhraseRelationRanker.load(Files.newInputStream(assets.resolve("relation_ranker.b64"))) : null);'
    assert source.count(anchor)==1
    source=source.replace(anchor,anchor[:-2]+''',
            SentenceLanguageRanker.load(Files.newInputStream(assets.resolve("sentence_language.b64"))),
            DirectCodeGenerator.load(Files.newInputStream(assets.resolve("code_generator.b64"))));
        IntegratedEvaluation.assets=assets;
        QuickDecoder baseline=IntegratedEvaluation.decoder(dictionary,null);''')
    for name,call in [('old','baseline.decode(fields[1],learned,fields[0])'),
                      ('updated','baseline.decode(fields[1],learned,fields[0],preferences)')]:
        anchor='                List<String> '+name+'=decoder.decode(fields[1],learned,fields[0]'+(');' if name=='old' else ',preferences);')
        assert source.count(anchor)==1
        source=source.replace(anchor,anchor+'\n                if(!'+name+'.equals('+call+')) throw new AssertionError("Single learned display differs from parent");')
    path=stage/'ContextLearningEvaluation.java';path.write_text(source)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-cp',str(classes),
        '-d',str(classes),str(path),str(folder/'ProtectionCheck.java')],check=True)
    text=(ROOT/'tools/PairedRankingPerformance.java').read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    assert text.count(anchor)==1
    text=text.replace(anchor,'''            if(Files.exists(assets.resolve("sentence_language.b64"))) {
                Class<?> slm=classes.loadClass(pkg+"SentenceLanguageRanker");types.add(slm);
                values.add(slm.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("sentence_language.b64"))));
            }
            if(Files.exists(assets.resolve("code_generator.b64"))) {
                Class<?> gen=classes.loadClass(pkg+"DirectCodeGenerator");types.add(gen);
                values.add(gen.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("code_generator.b64"))));
            }
'''+anchor)
    path=WORK/'PairedRankingPerformance.java';path.write_text(text)
    subprocess.run(['javac','-encoding','UTF-8','-d',str(WORK/'performance-classes'),str(path)],check=True)
    # Choose changed-display fixtures without consulting target/rank labels.
    rows=(WORK/'inputs.tsv').read_text().splitlines();pred=(WORK/'predictions.tsv').read_text().splitlines()
    selected=[]
    for before,after in zip(rows,pred):
        if before.split('\t')[3]!=after.split('\t')[3]:selected.append(before)
        if len(selected)==4:break
    (WORK/'protection-inputs.tsv').write_text(''.join(s+'\n' for s in selected))
    android=WORK/'android'
    if android.exists():raise ValueError('Preserve Android archive')
    android.mkdir()
    blob=subprocess.check_output(['git','archive',BASELINE],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:archive.extractall(android,filter='data')
    package='app/src/main/java/hk/cantonesemixeng/keyboard/'
    for name in ('QuickDecoder','TailSupplement','DirectCodeGenerator'):
        shutil.copyfile(stage/package/(name+'.java'),android/package/(name+'.java'))
    path=android/package/'CantoneseMixEngKeyboardService.java';path.write_text(service_source(path.read_text()))
    shutil.copyfile(DATA/'code_generator.b64',android/'app/src/main/assets/code_generator.b64')
    shutil.copyfile(ROOT/'app/src/main/assets/stroke.tsv',android/'app/src/main/assets/stroke.tsv')
    shutil.copytree(ROOT/'app/src/main/assets/licenses/stroke',android/'app/src/main/assets/licenses/stroke')
    paths=[folder/'prepare_guards.py',folder/'ProtectionCheck.java',stage/'ContextLearningEvaluation.java',
        WORK/'PairedRankingPerformance.java',WORK/'protection-inputs.tsv']
    paths += [p for p in sorted((android/'app/src/main').rglob('*')) if p.is_file()]
    write(DATA/'guard-wiring-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        policy='Same frozen model/policy. Exact optional service loader+constructor wired for Android checks; no APK.'))
    print('Single/protection/timing harnesses and exact wired Android candidate staged')


if __name__=='__main__':main()
