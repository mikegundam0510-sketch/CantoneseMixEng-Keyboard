"""Controlled JVM baseline comparison; this is not an Android total-PSS measurement."""
import json, pathlib, subprocess, tempfile, statistics
root=pathlib.Path(__file__).resolve().parent.parent
baseline='0279ea5f0daaf18770fc50a977d73d204fff3d35'
classes=('DictionaryEngine','QuickDecoder','OfflineLanguageModel','EnglishEngine')
report={}
with tempfile.TemporaryDirectory() as tmp:
    for revision in ('before','after'):
        directory=pathlib.Path(tmp)/revision;directory.mkdir()
        sources=[]
        for name in classes:
            source='app/src/main/java/hk/kaiboard/android/'+name+'.java'
            path=directory/(name+'.java')
            path.write_text(subprocess.check_output(['git','show',baseline+':'+source],cwd=root,text=True) if revision=='before' else (root/source).read_text())
            sources.append(str(path))
        subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(root/'app/src/main/java'),
            '-d',str(directory),*sources,str(root/'tools/LoadingBenchmark.java')],check=True)
        runs=[json.loads(subprocess.check_output(['java','-Xms256m','-Xmx512m','-cp',str(directory),'LoadingBenchmark'],cwd=root,text=True)) for _ in range(3)]
        report[revision]={'runs':runs, 'median':{k:statistics.median(r[k] for r in runs) for k in ('basic_ms','full_ms','heap_bytes','english_alloc_bytes')}}
    # Ranking deliberately changes with the HK usage/symbol fix. Exact-code and
    # first-choice behavior are validated by the decoder regression tests.
out=root/'ui-evidence';out.mkdir(exist_ok=True)
(out/'loading-benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v['median'] for k,v in report.items()},ensure_ascii=False),flush=True)
