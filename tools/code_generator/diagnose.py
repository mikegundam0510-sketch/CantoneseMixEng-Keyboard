"""Post-rejection implementation checks; no model or policy selection."""
import gzip,json,time
import numpy as np
from common import ROOT,DATA,WORK,REPORTS,frozen,write,digest
from model import load,Codec,decode,batch,forward


def alignments(codec,code,text):
    cache={}
    def count(pos,at):
        if at==len(text):return int(pos==len(code))
        if (pos,at) in cache:return cache[pos,at]
        total=0
        for n in (1,2):
            if pos+n<=len(code) and code[pos:pos+n] in codec.codes.get(text[at],[]):total+=count(pos+n,at+1)
        cache[pos,at]=min(2,total);return cache[pos,at]
    return count(0,0)


def diagnose():
    frozen();selection=json.loads((DATA/'selection.json').read_text());assert selection['selected'] is None
    rows=[json.loads(s) for s in gzip.decompress((WORK/'corpus.jsonl.gz').read_bytes()).decode().splitlines()][:40]
    parity={};codes=json.loads((DATA/'codes.json').read_text())
    for arm in ('teacher','contrast'):
        v,chars=load(DATA/'models'/(arm+'.npz'));codec=Codec(chars,codes)
        for value in v.values():value.flags.writeable=False
        checked=0;maximum=0.
        for r in rows:
            values=decode(v,codec,r['code'],r['context'])
            unambiguous=[(t,s) for t,s in values if alignments(codec,r['code'],t)==1]
            if not unambiguous:continue
            packed=[dict(code=r['code'],context=r['context'],text=t) for t,s in unambiguous]
            scores,_=forward(v,batch(packed,codec),codec)
            for actual,(text,score) in zip(scores,unambiguous):
                delta=abs(float(actual)-score/len(r['code']));maximum=max(maximum,delta)
                if delta>1e-5:raise AssertionError('Beam/teacher conditional-score mismatch')
                checked+=1
                if checked==80:break
            if checked==80:break
        assert checked==80
        parity[arm]=dict(unambiguous_generated_paths=checked,max_absolute_score_error=maximum,immutable_weights=True)
    write(REPORTS/'beam-score-parity.json',parity)
    # Model-only host research timing, with no Java/Android overhead included.
    v,chars=load(DATA/'models/contrast.npz');codec=Codec(chars,codes)
    cases=['ofonaovrmrq','hmerrrysmlrp','dpofvivcjutrmyyjvcqnjd','ofykrmmsydwljpvwjd','vkmmnkmrvordrjjj','hi'*24]
    for i in range(3):
        for code in cases:decode(v,codec,code)
    timing=[]
    for code in cases:
        wall=[];cpu=[]
        for i in range(7):
            start=time.perf_counter_ns();cstart=time.thread_time_ns();values=decode(v,codec,code)
            cpu.append((time.thread_time_ns()-cstart)/1e6);wall.append((time.perf_counter_ns()-start)/1e6)
        timing.append(dict(code=code,letters=len(code),wall_median_ms=float(np.median(wall)),cpu_median_ms=float(np.median(cpu)),candidates=len(values)))
    write(REPORTS/'model-only-timing.json',dict(warmup=3,samples=7,cases=timing,standalone_numpy_only=True,
        excludes_native_parent_fusion_loader_and_android=True,not_app_latency_or_an_adoption_gate=True))
    print(json.dumps(dict(parity=parity,standalone_timing_complete=True)))


if __name__=='__main__':diagnose()
