"""Quiet paired same-JVM timing with both deployed and search models enabled."""
import argparse
import subprocess
from experiment import ROOT,DATA,WORK,REPORTS,digest,write,frozen
from evaluate import check


def performance(arm):
    frozen();check(arm);host=WORK/('performance-'+arm);host.mkdir()
    java=(ROOT/'tools/PairedRankingPerformance.java').read_text()
    anchor='            decoder = decoderClass.getConstructor(types.toArray(new Class<?>[0])).newInstance(values.toArray());'
    assert java.count(anchor)==1
    java=java.replace(anchor,'''            if(Files.exists(assets.resolve("sentence_language.b64"))) {
                Class<?> slm=classes.loadClass(pkg+"SentenceLanguageRanker");types.add(slm);
                values.add(slm.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("sentence_language.b64"))));
            }
            if(Files.exists(assets.resolve("search_language.b64"))) {
                types.add(9,double.class);values.add(9,1.5d);
                Class<?> slm=classes.loadClass(pkg+"SearchLanguageRanker");types.add(slm);
                values.add(slm.getMethod("load",InputStream.class).invoke(null,Files.newInputStream(assets.resolve("search_language.b64"))));
            }
'''+anchor)
    p=host/'PairedRankingPerformance.java';p.write_text(java)
    subprocess.run(['javac','-encoding','UTF-8','-d',str(host/'classes'),str(p)],check=True)
    write(host/'before-timing-freeze.json',dict(base_harness_sha256=digest(ROOT/'tools/PairedRankingPerformance.java'),
        wired_harness_sha256=digest(p),warmup=30,samples=11,actual_both_models_enabled=True))
    baseline=WORK/'baseline';candidate=WORK/arm;raw=REPORTS/('timing-'+arm+'.tsv')
    if raw.exists():raise ValueError('Do not overwrite timing')
    with raw.open('x') as stream:
        subprocess.run(['java','-Xmx1g','-cp',str(host/'classes'),'PairedRankingPerformance',
            str(baseline/'classes'),str(baseline/'app/src/main/assets'),str(candidate/'classes'),str(candidate/'app/src/main/assets'),'30','11'],stdout=stream,check=True)
    lines=raw.read_text().splitlines();assert lines[0]=='# warmup=30 samples=11'
    rows=[]
    for line in lines[2:]:
        code,n,bw,aw,bc,ac=line.split('\t');bw,aw,bc,ac=map(float,(bw,aw,bc,ac))
        rows.append(dict(code=code,letters=int(n),before_wall_ms=bw,after_wall_ms=aw,before_cpu_ms=bc,after_cpu_ms=ac,wall_ratio=aw/bw,cpu_ratio=ac/bc))
    assert len(rows)==6;maximum=max(max(r['wall_ratio'],r['cpu_ratio']) for r in rows)
    value=dict(arm=arm,warmup=30,samples=11,cases=rows,max_ratio=maximum,qualified=maximum<=1.2,
        raw_sha256=digest(raw),wired_harness_sha256=digest(p),actual_both_models_enabled=True,physical_device=False)
    write(REPORTS/('timing-'+arm+'.json'),value);print('max_ratio',maximum,'qualified',value['qualified'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('arm',choices=['language','trained']);a=p.parse_args();performance(a.arm)
