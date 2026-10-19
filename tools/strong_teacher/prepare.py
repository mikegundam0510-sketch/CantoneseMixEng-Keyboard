"""Prepare a known diagnostic, without claiming another unseen500 evaluation."""
import hashlib
import json
from pathlib import Path
import subprocess
from constraints import read_facts,accept,align,grammar

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'tools/data/strong_teacher'
WORK=ROOT/'.native/strong-teacher-20261019'
REPORTS=ROOT/'tools/reports/strong-teacher-2026-10-19'
ENV=Path('/workspace/cantonese-teacher-environment')
BASELINE='9c183b7baaa0c3cccb5d513c3d5abb07903e4fe5'
LLAMA='d7a695ef679138c13d86359b84c1731d36213d32'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as out:out.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')


def main():
    if DATA.exists() or REPORTS.exists():raise ValueError('Preserve existing preparation')
    DATA.mkdir(parents=True);REPORTS.mkdir(parents=True)
    native=ROOT/'.native/retained-pool-20261019/native'
    reference=ROOT/'tools/reports/retained-pool-2026-10-19/independent500-parent.tsv'
    previous=[s.split('\t') for s in reference.read_text().splitlines()]
    if len(previous)!=500 or any(f[1] for f in previous):raise ValueError('Expected the observed cold500 pool')
    selected=[]
    for kind,condition in [('cold-top5',lambda r:1<=r<=5),('cold-late',lambda r:6<=r<=20),('cold-missing',lambda r:r==0)]:
        rows=[f for f in previous if condition(int(f[4]))]
        rows.sort(key=lambda f:hashlib.sha256(('strong-teacher-v1\t'+'\t'.join(f[:4])).encode()).hexdigest())
        if len(rows)<20:raise ValueError('Insufficient diagnostic stratum')
        for f in rows[:20]:selected.append([kind]+f[1:])
    facts=read_facts(WORK/'native-facts.tsv')
    contexts=[];context_provenance=[]
    for n,line in enumerate((ROOT/'tools/hk_daily_context_cases.tsv').read_text().splitlines()):
        if not line or line.startswith('#'):continue
        f=line.split('\t');sizes=align(f[1],f[2],facts)
        if sizes is None or len(f[2])<6:raise ValueError('Authored context source changed')
        # A controlled supplied-context test: the first four already-typed
        # characters are removed from BOTH the target and remaining code.
        cut=4;consumed=sum(sizes[:cut]);prefix=f[0]+f[2][:cut]
        contexts.append([f'context32-{n}',prefix,f[1][consumed:],f[2][cut:]])
        context_provenance.append(dict(case=f'context32-{n}',original_source_line=n,
            prefix_characters=cut,consumed_code_keys=consumed,alignment=sizes))
    if len(contexts)!=32:raise ValueError('Context diagnostic changed')
    inp=WORK/'context-parent-inputs.tsv';out=WORK/'context-parent.tsv'
    with inp.open('x') as data:
        for f in contexts:data.write('\t'.join(f[:3])+'\n')
    result=subprocess.run(['java','-Xmx1g','-cp',str(native/'classes'),'hk.cantonesemixeng.keyboard.DeployedEvaluation',
        str(native/'app/src/main/assets'),str(inp),str(out)],check=True,capture_output=True,text=True)
    (REPORTS/'native-context.txt').write_text(result.stdout)
    predictions=out.read_text().splitlines()
    if len(predictions)!=32:raise ValueError('Partial native contextual result')
    for f,line in zip(contexts,predictions):
        p=line.split('\t');values=p[3].split('|') if p[3] else []
        if p[:3]!=f[:3]:raise ValueError('Context input mismatch')
        selected.append(['context32',f[1],f[2],f[3],str(values.index(f[3])+1 if f[3] in values else 0),p[3]])
    prompts=WORK/'rerank';prompts.mkdir();generated=WORK/'grammars';generated.mkdir()
    generation_ids=[]
    with (DATA/'cases.tsv').open('x') as cases,(WORK/'rerank-manifest.txt').open('x') as manifest:
        for n,f in enumerate(selected):
            kind,context,code,target,rank,joined=f
            if not accept(code,target,facts):raise ValueError('Reference code is not native legal')
            values=joined.split('|') if joined else []
            if not values or any(not accept(code,t,facts) for t in values):raise ValueError('Invalid parent display')
            cases.write('\t'.join([str(n)]+f)+'\n')
            prompt=prompts/(str(n)+'.txt')
            # Gold/rank and source stratum are absent from the likelihood input.
            prompt.write_text(context+'\n'+'\n'.join(values)+'\n');manifest.write(str(prompt)+'\n')
            if kind=='cold-missing' or (kind=='context32' and len([i for i in generation_ids if i>=60])<8):
                (generated/(str(n)+'.gbnf')).write_text(grammar(code,facts));generation_ids.append(n)
    paths=[reference,ROOT/'tools/hk_daily_context_cases.tsv',DATA/'cases.tsv',WORK/'native-facts.tsv',
        ENV/'requirements.lock']+sorted((ROOT/'tools/strong_teacher').glob('*.py'))
    paths+=sorted((ROOT/'tools/strong_teacher').glob('*.cpp'))+sorted((ROOT/'tools/strong_teacher').glob('*.java'))
    protocol=dict(parent_revision=BASELINE,scope='Known stratified diagnostic only, not fresh independent or population-weighted accuracy. The preceding500 is already consumed. No app adoption or distillation in this phase.',
        data='Twenty each observed cold-top5/cold-late/cold-missing, fixed hash order. The old context32 source actually contains no initial context. Make32 controlled supplied-context cases by taking the first4 already-typed characters from each authored whole sentence and removing their exact native alignment from the remaining code and target. No invented conversation or new independent claim. Gold/ranks only select cold diagnostic strata and calculate results, never enter teacher inference. No fitting.',
        reranking='All92 ordinary native pools, maximum20 each; primary sum of teacher continuation token log probabilities divided by Han character count. Stable native order on ties; entire20 set retained, first may change in this offline diagnostic. Report gains AND losses at first/top5/top20 separately per stratum. Raw sums secondary descriptive only; no score/prompt search.',
        generation=dict(case_ids=generation_ids,samples=4,seeds=[0,1,2,3],temperature=[0,.7,.7,.7],top_k=40,top_p=.9,max_tokens=192,
            policy='Full native single-Han dictionary, all1/2-key aliases, finite GBNF exactly consumes input, no vocabulary frequency cut. Grammar compiled without reference text. Validate outputs again through actual Java dictionary. Report exact generation hits, timeouts, incomplete/invalid results and union oracle separately. Four samples are not a displayed20 accuracy claim.'),
        model='Proposed Qwen3-4B-Instruct-2507 Q4_K_M, CPU only. Model identity/license/source commit/LFS SHA remain UNVERIFIED until Hugging Face access is enabled. Do not run this protocol on an unpinned substitute. Freeze actual model and inference bytes before outcomes.',
        runtime=dict(llama_commit=LLAMA,threads=4,ctx=2048,model_file_currently_available=False),
        network='Hugging Face returned proxy CONNECT403. Draft revision4 adds huggingface.co and cas-bridge.xethub.hf.co, requires review/save/publish. No proxy/TLS bypass.',
        preparation_audit='Earlier no-context preparation and its protocol/source are preserved under .native/strong-teacher-preflight-no-context-20261019 before any model inference. This is a data-preparation correction, not outcome-based tuning.',
        sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in paths})
    if sum(bool(f[1]) for f in selected)!=32:raise ValueError('Supplied contexts missing')
    write(DATA/'context-provenance.json',context_provenance)
    write(DATA/'protocol.json',protocol)
    write(DATA/'seal.json',dict(protocol_sha256=sha(DATA/'protocol.json'),before_any_teacher_outputs=True,model_inference_freeze_pending=True))
    print('Prepared92 known diagnostic inputs and28 code-only generation grammars; no model inference')


if __name__=='__main__':main()
