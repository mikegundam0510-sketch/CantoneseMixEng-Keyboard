#!/usr/bin/env python3
"""Native frozen-baseline comparison; selection must precede opening heldout800."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from prefix_features import encode
from prepare_tatoeba_corpus import digest
from train_phrase_model import ROOT

DATA=ROOT/'tools/data/daily_prefix'
BASELINE=json.loads((DATA/'protocol.json').read_text())['baseline_revision']

def build(work,trial=False,initial_policy=False):
    work.mkdir(parents=True,exist_ok=True)
    optional=work/'app/src/main/assets/prefix_ranker.b64'
    if optional.exists():optional.unlink()  # Remove only a prior generated experiment asset.
    archive=subprocess.check_output(['git','archive',BASELINE,'app/src/main/java','app/src/main/assets','tools/RankingEvaluation.java'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as data:data.extractall(work,filter='data')
    if trial:
        for name in ('QuickDecoder','SentenceRanker','PrefixRanker'):
            relative=f'app/src/main/java/hk/cantonesemixeng/keyboard/{name}.java'
            shutil.copyfile(ROOT/relative,work/relative)
        if initial_policy:
            quick=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
            source=quick.read_text();start=source.index('    private List<Path> reservePrefixes(');end=source.index('    private String lookaheadContext',start)
            quick.write_text(source[:start]+(DATA/'initial-reserve.java.txt').read_text()+source[end:])
    driver=work/'tools/RankingEvaluation.java';text=driver.read_text()
    text=text.replace('List<String> values = decoder.decode(fields[1]',
        'if(fields.length==4) fields=Arrays.copyOfRange(fields,1,4);\n                List<String> values = decoder.decode(fields[1]')
    if trial:
        text=text.replace('? SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))) : null);',
            '? SentenceRanker.load(Files.newInputStream(assets.resolve("sentence_ranker.b64"))) : null,\n            Files.exists(assets.resolve("prefix_ranker.b64")) ? PrefixRanker.load(Files.newInputStream(assets.resolve("prefix_ranker.b64"))) : null);')
    driver.write_text(text)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(driver)],check=True)

def run(work,cases,output):
    process=subprocess.Popen(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.RankingEvaluation',
        str(work/'app/src/main/assets'),str(cases.resolve()),str(output.resolve())])
    try:
        code=process.wait()
        if code:raise subprocess.CalledProcessError(code,process.args)
    except BaseException:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        raise
    return read_results(cases,output)

def read_results(cases,output):
    groups=defaultdict(list)
    inputs=[s.split('\t') for s in cases.read_text().splitlines() if s and not s.startswith('#')]
    results=[s.split('\t') for s in output.read_text().splitlines()]
    if len(inputs)!=len(results):raise ValueError('Partial evaluation')
    for case,result in zip(inputs,results):
        if result[:len(case)]!=case:raise ValueError('Evaluation order changed')
        groups[case[0].split(':',1)[-1] if len(case)==4 else 'written800'].append(int(result[len(case)]))
    return {name:dict(cases=len(ranks),top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),
        top20=sum(r>0 for r in ranks),mrr=sum(1/r for r in ranks if r)/len(ranks)) for name,ranks in groups.items()}

def validation(weights, cases,output,initial_policy=False):
    output.mkdir(parents=True,exist_ok=True);build(output/'base');build(output/'trial',True,initial_policy)
    # A matching input alone cannot prove a cached output used this baseline.
    cache=output/'baseline-cache.json';baseline=output/'baseline.tsv'
    identity={'revision':BASELINE,'cases_sha256':digest(cases)}
    expected={**identity,'output_sha256':digest(baseline)} if baseline.exists() else None
    if expected and cache.exists() and json.loads(cache.read_text())==expected:before=read_results(cases,baseline)
    else:
        before=run(output/'base',cases,baseline)
        cache.write_text(json.dumps({**identity,'output_sha256':digest(baseline)},sort_keys=True)+'\n')
    trials={}
    parameters=json.loads(weights.read_text());protocol=json.loads((DATA/'protocol.json').read_text())
    def trial(strength):
        work=output/f'grid-{strength:g}'
        shutil.copytree(output/'trial',work,dirs_exist_ok=True)
        (work/'app/src/main/assets/prefix_ranker.b64').write_bytes(encode(parameters,strength))
        return strength,run(work,cases,output/f'trial-{strength:g}.tsv')
    with ThreadPoolExecutor(max_workers=2) as executor:
        for strength,result in executor.map(trial,protocol['strength_grid']):trials[strength]=result
    eligible=[s for s,v in trials.items() if all(v[n][k]>=b[k] for n,b in before.items() for k in ('top1','top5'))]
    selected=max(eligible,key=lambda s:(sum(v['mrr'] for v in trials[s].values()),-s)) if eligible else 0
    # A passing but ineffective scorer is not shipped merely because it exists.
    if selected and sum(v['mrr'] for v in trials[selected].values())<=sum(v['mrr'] for v in before.values()):selected=0
    decision={'baseline':before,'trials':trials,'eligible':eligible,'selected_strength':selected,
        'protocol_sha256':digest(DATA/'protocol.json'),'weights_sha256':digest(weights),
        'search_policy_sha256':digest(DATA/('protocol.json' if initial_policy else 'relative-protocol.json')),
        'runtime_source_sha256':{name:digest(ROOT/f'app/src/main/java/hk/cantonesemixeng/keyboard/{name}.java') for name in ('QuickDecoder','PrefixRanker')},
        'validation_cases_sha256':digest(cases),'selection_before_heldout':True}
    (output/'selection.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n');print(json.dumps(decision))
    return decision

def heldout(weights,cases,output,decision):
    chosen=json.loads(decision.read_text());strength=chosen['selected_strength']
    if digest(weights)!=chosen['weights_sha256']:raise ValueError('Selected weights changed')
    for name,checksum in chosen.get('runtime_source_sha256',{}).items():
        if digest(ROOT/f'app/src/main/java/hk/cantonesemixeng/keyboard/{name}.java')!=checksum:raise ValueError('Selected runtime changed')
    if chosen.get('search_policy_sha256') and digest(DATA/'relative-protocol.json')!=chosen['search_policy_sha256']:raise ValueError('Selected search protocol changed')
    output.mkdir(parents=True,exist_ok=True);build(output/'base');build(output/'trial',True)
    if strength:(output/'trial/app/src/main/assets/prefix_ranker.b64').write_bytes(encode(json.loads(weights.read_text()),strength))
    with ThreadPoolExecutor(max_workers=2) as executor:
        prior=executor.submit(run,output/'base',cases,output/'baseline.tsv')
        selected=executor.submit(run,output/'trial',cases,output/'selected.tsv')
        before,after=prior.result(),selected.result()
    audit=json.loads((DATA/'exposure-audit.json').read_text())
    if digest(cases)==json.loads((DATA/'manifest.json').read_text())['file_sha256']['heldout.tsv']:
        def novel(path):
            rows=[line.split('\t') for line in path.read_text().splitlines()]
            ranks=[int(r[3]) for r in rows if r[2] not in audit['known_training_or_vocabulary_overlap']]
            return dict(cases=len(ranks),top1=sum(r==1 for r in ranks),top5=sum(0<r<=5 for r in ranks),
                top20=sum(r>0 for r in ranks),mrr=sum(1/r for r in ranks if r)/len(ranks))
        before['written799']=novel(output/'baseline.tsv');after['written799']=novel(output/'selected.tsv')
    report={'before':before,'after':after,'selected_strength':strength,'selection_sha256':digest(decision),
        'cases_sha256':digest(cases),'exposure_audit_sha256':digest(DATA/'exposure-audit.json')}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('weights','cases','output'):p.add_argument(n,type=Path)
    p.add_argument('--selection',type=Path);p.add_argument('--initial-policy',action='store_true');a=p.parse_args()
    if a.selection:heldout(a.weights,a.cases,a.output,a.selection)
    else:validation(a.weights,a.cases,a.output,a.initial_policy)
