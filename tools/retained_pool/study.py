"""Retain the deployed pool, add only new-character proposals; one fixed trial."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'tools/code_generator'))
from model import load, Codec, decode
from report_prefix_retrieval import compare

BASELINE = '1b13d0173ef0d8d95ea2d4871e528d9c82824e65'
DATA = ROOT/'tools/data/retained_pool'
WORK = ROOT/'.native/retained-pool-20261019'
REPORTS = ROOT/'tools/reports/retained-pool-2026-10-19'
PREVIOUS = ROOT/'.native/vocabulary-expansion-20261018'
CHECKPOINT = ROOT/'tools/data/vocabulary_expansion/models/expanded.npz'
CODES = ROOT/'tools/data/vocabulary_expansion/codes.json'
KNOWN = {
    'calibration1450': (
        ROOT/'tools/data/context_search/calibration1450.tsv',
        ROOT/'tools/reports/tail-supplement-2026-10-18/native-calibration1450.tsv'),
    'guard3893': (
        ROOT/'.native/joint-ranking-20261015/guard-cases3893.tsv',
        ROOT/'tools/reports/tail-supplement-2026-10-18/native-guard3893.tsv')}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        out.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def verify():
    protocol = json.loads((DATA/'protocol.json').read_text())
    if sha(DATA/'protocol.json') != json.loads((DATA/'seal.json').read_text())['protocol_sha256']:
        raise ValueError('Retained-pool protocol changed')
    for name, wanted in protocol['sha256'].items():
        if sha(ROOT/name) != wanted:
            raise ValueError('Frozen source/input changed: '+name)
    return protocol


def verify_inference():
    verify()
    for name, wanted in json.loads((DATA/'inference-freeze.json').read_text())['sha256'].items():
        if sha(ROOT/name) != wanted:
            raise ValueError('Frozen inference changed: '+name)


def prepare():
    if any(p.exists() for p in (DATA, WORK, REPORTS)):
        raise ValueError('Preserve prior trial; declare new paths instead')
    parent_tree = subprocess.check_output(['git','rev-parse',BASELINE+':app'], cwd=ROOT, text=True).strip()
    deployed_tree = subprocess.check_output(['git','rev-parse','d7dec75:app'], cwd=ROOT, text=True).strip()
    if parent_tree != deployed_tree:
        raise ValueError('Cached parent displays are not the deployed app')
    _, chars = load(CHECKPOINT)
    _, oldchars = load(ROOT/'tools/data/code_generator/models/teacher.npz')
    additions = ''.join(c for c in chars if c not in set(oldchars))
    if len(additions) != 245 or not set(oldchars).issubset(chars):
        raise ValueError('Unexpected frozen alphabet')
    paths = sorted(HERE.glob('*.java'))+[Path(__file__),CHECKPOINT,CODES,
        ROOT/'tools/data/vocabulary_expansion/inference-freeze.json',
        ROOT/'tools/data/vocabulary_expansion/compat-protocol.json',
        ROOT/'tools/data/code_generator/models/teacher.npz',
        ROOT/'tools/data/code_generator/codes.json',
        ROOT/'tools/code_generator/model.py',
        ROOT/'tools/tail_supplement/NativeEvaluation.java',
        ROOT/'tools/tail_supplement/PolicyTest.java',
        ROOT/'tools/report_prefix_retrieval.py',
        ROOT/'tools/data/vocabulary_expansion/reserve.tsv',
        ROOT/'tools/data/vocabulary_expansion/reserve-source.jsonl']
    paths += [p for row in KNOWN.values() for p in row]
    # Seal the existing ordinary generation caches. They are known outcomes,
    # not new independent evidence. The compatibility guard cache omitted short
    # native lists; those inputs receive ordinary generation in this trial.
    paths += [PREVIOUS/f'{prefix}generated-{part}.tsv'
              for prefix in ('','guard-') for part in range(4)]
    protocol = dict(parent_revision=BASELINE, parent_app_tree=parent_tree,
        reason='The observed replacement trial lost four old-alphabet targets during generation. Preserve that rejected trial. This new policy retains the deployed complete pool and limits expanded offers to strings containing a TRAIN-selected addition.',
        policy='First run the complete deployed pipeline including the old generator. Keep all its at-most20 choices in the comparison pool. Freeze min(18,deployed-count), including previous generated choices. Expanded model uses its unchanged ordinary beam24/top20; filter to strings containing at least one of the245 TRAIN-only new letters. No search beyond those20 after filtering. Existing TailSupplement competes at most2 final slots on unchanged native whole-text score; exact codes, old-before-new ties, native relative order, total<=20. Original personal/Single/mixed/translation safeguards apply. Keeping all in pool does not promise all20 remain displayed.',
        model='Exactly the already trained/rejected expanded checkpoint, no fitting, source additions, target lookup, threshold sweep or score tuning. Original2248 teacher stays active unchanged.',
        score='QuickDecoder.languageScore(context,text)+SentenceRanker.score(context,text)+alignedRelation(raw(context,text),raw(context,deployed-head)); same as deployed tail scorer. No neural proposal score in final ranking.',
        known_gates='Known1450: deployed first18 exact, first/top5 counts unchanged, aggregate top20 gain, each named set nondecreasing. Then known3893: first18 exact and all aggregate/each-set first/top5/top20 counts nondecreasing. Report gains and losses. Stop on failed gate.',
        later_gates='If known sets qualify: exact Java expanded-provider parity and full ordinary pipeline vs screening; optional/personal/mixed/translation fallback; Single32; exact wired Android unit/Lint; isolated paired30warm11 sixcode wall/CPU<=1.2. Freeze exact source/model/classes. Only then one current-parent/candidate pass on unused vocabulary_expansion/reserve500; no count loss and positive top20 gain. No independent-based tuning.',
        reserve='Both earlier500 sets are observed. The newly isolated500 is unused and remains so unless all known/native/learning/build/timing gates pass. Never train or select vocabulary from these examples.',
        delivery='No APK/version/signing/storage/layout changes. Adopt only after every gate passes; otherwise keep deployed d7dec75 app and publish failed research with unrun checks explicit.',
        additions=additions,
        sha256={str(p.relative_to(ROOT)):sha(p) for p in paths})
    write(DATA/'protocol.json',protocol)
    write(DATA/'seal.json',dict(protocol_sha256=sha(DATA/'protocol.json'),before_fusion_predictions=True))
    WORK.mkdir(parents=True);REPORTS.mkdir(parents=True)
    (DATA/'additions.txt').write_text(additions+'\n')
    stage=WORK/'native';stage.mkdir()
    blob=subprocess.check_output(['git','archive',BASELINE,'app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
        archive.extractall(stage,filter='data')
    # Reuse the frozen target-free native scorer; the only additional operation
    # before TailSupplement is the declared new-character filter.
    original=(ROOT/'tools/tail_supplement/NativeEvaluation.java').read_text()
    original=original.replace('public final class NativeEvaluation','public final class NativeFusionEvaluation')
    anchor='List<String> parent = values(f[3]), proposals = values(f[4]);'
    if original.count(anchor)!=1:raise ValueError('Native scoring harness changed')
    original=original.replace(anchor,anchor+'\n                proposals = NewCharacterSupplement.filter(proposals, additions);')
    anchor='int count = 0, changed = 0, additions = 0;'
    # Avoid shadowing the existing integer additions audit.
    original=original.replace('filter(proposals, additions)','filter(proposals, newLetters)')
    original=original.replace(anchor,'Set<Integer> newLetters = new HashSet<>();\n        Files.readString(Path.of(args[4])).strip().codePoints().forEach(newLetters::add);\n        '+anchor)
    source=WORK/'NativeFusionEvaluation.java';source.write_text(original)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-d',str(stage/'classes'),
        str(source),str(HERE/'NewCharacterSupplement.java'),str(HERE/'FusionPolicyTest.java'),
        str(ROOT/'tools/tail_supplement/PolicyTest.java')],check=True)
    with (REPORTS/'policy-checks.txt').open('x') as out:
        for test in ('PolicyTest','FusionPolicyTest'):
            result=subprocess.check_output(['java','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.'+test],text=True)
            out.write(result);print(result.strip())
    frozen=[source, DATA/'additions.txt']+sorted((stage/'classes').rglob('*.class'))
    frozen+=sorted(p for p in (stage/'app/src/main/assets').rglob('*') if p.is_file())
    write(DATA/'inference-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in frozen},
        before_fusion_predictions=True,protocol_sha256=sha(DATA/'protocol.json')))
    print('Fixed fusion policy sealed; no fusion outcomes yet')


def inputs(name, part=None):
    verify_inference()
    rows=KNOWN[name][0].read_text().splitlines()
    parents=KNOWN[name][1].read_text().splitlines()
    if len(rows)!=len(parents):raise ValueError('Partial parent output')
    prefix='' if name=='calibration1450' else 'guard-'
    cached=[None]*len(rows)
    for shard in range(4):
        values=(PREVIOUS/f'{prefix}generated-{shard}.tsv').read_text().splitlines()
        if len(values)!=len(rows[shard::4]):raise ValueError('Partial generation cache')
        cached[shard::4]=values
    suffix='' if part is None else '-'+str(part)
    output=WORK/(name+'-inputs'+suffix+'.tsv')
    pending=output.with_suffix('.pending.tsv')
    if output.exists() or pending.exists():raise ValueError('Preserve existing/partial target-free inputs')
    v=codec=None;regenerated=0
    with pending.open('x') as out:
        indices=range(len(rows)) if part is None else range(part,len(rows),4)
        for n in indices:
            f,b,g=[s.split('\t') for s in (rows[n],parents[n],cached[n])]
            if f!=b[:4] or f[:3]!=g[:3]:raise ValueError('Cache input identity differs')
            proposed=g[-1]
            # Only the old compatibility guard skipped ordinary inference on
            # short lists. Restore these without using gold or old target ranks.
            if name=='guard3893' and not proposed:
                if v is None:
                    v,chars=load(CHECKPOINT);codec=Codec(chars,json.loads(CODES.read_text()))
                    for a in v.values():a.setflags(write=False)
                proposed='|'.join(t for t,s in decode(v,codec,f[2],f[1],beam=24))
                regenerated+=1
            out.write('\t'.join(f[:3]+[b[5],proposed])+'\n')
    pending.rename(output)
    print(name,'part',part,'restored ordinary skipped generation',regenerated,flush=True)


def run(name):
    verify_inference()
    if name=='guard3893' and not json.loads((REPORTS/'calibration1450.json').read_text())['qualified']:
        raise ValueError('Known calibration gate failed')
    path=WORK/(name+'-inputs.tsv')
    if not path.exists():
        count=len(KNOWN[name][0].read_text().splitlines());rows=[None]*count
        for part in range(4):
            shard=(WORK/(name+'-inputs-'+str(part)+'.tsv')).read_text().splitlines()
            if len(shard)!=len(rows[part::4]):raise ValueError('Partial inputs')
            rows[part::4]=shard
        with path.open('x') as out:out.write(''.join(s+'\n' for s in rows))
    stage=WORK/'native';output=WORK/(name+'-predictions.tsv')
    if output.exists():raise ValueError('Preserve completed predictions')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.NativeFusionEvaluation',
        str(stage/'app/src/main/assets'),str(path),str(output),str(REPORTS/(name+'-scores.tsv')),str(DATA/'additions.txt')],check=True)


def report(name):
    verify_inference()
    cases=KNOWN[name][0].read_text().splitlines();parents=KNOWN[name][1].read_text().splitlines()
    predictions=(WORK/(name+'-predictions.tsv')).read_text().splitlines()
    if not len(cases)==len(parents)==len(predictions):raise ValueError('Partial fusion output')
    output=REPORTS/(name+'.tsv');newchars=set((DATA/'additions.txt').read_text().strip())
    changes=additions=removals=0
    with output.open('x') as out:
        for case,parent,pred in zip(cases,parents,predictions):
            f,b,p=[s.split('\t') for s in (case,parent,pred)]
            if f!=b[:4] or f[:3]!=p[:3]:raise ValueError('Fusion identity differs')
            old=b[5].split('|') if b[5] else [];values=p[3].split('|') if p[3] else []
            pinned=min(18,len(old));novel=set(values)-set(old)
            if old[:pinned]!=values[:pinned] or len(values)>20 or len(values)!=len(set(values)):
                raise ValueError('Deployed prefix/display contract failed')
            if len(novel)>2 or any(not any(c in newchars for c in t) for t in novel):
                raise ValueError('New-character-only supplement failed')
            changes+=values!=old;additions+=len(novel);removals+=len(set(old)-set(values))
            rank=values.index(f[3])+1 if f[3] in values else 0
            out.write(case+'\t'+str(rank)+'\t'+p[3]+'\n')
    r=compare(KNOWN[name][0],KNOWN[name][1],output)
    r.update(baseline_revision=BASELINE,known_not_independent=True,
        display_changes=dict(cases=changes,added=additions,removed=removals),
        gates=dict(deployed_first18_identical=True,new_character_only=True,
            aggregate_counts_nondecreasing=all(r['after'][k]>=r['before'][k] for k in ('top1','top5','top20')),
            each_set_counts_nondecreasing=r['no_per_set_count_loss']))
    if name=='calibration1450':r['gates']['aggregate_top20_gain']=r['after']['top20']>r['before']['top20']
    r['qualified']=all(r['gates'].values())
    write(REPORTS/(name+'.json'),r)
    write(DATA/(name+'-decision.json'),dict(qualified=r['qualified'],reserve_decoded=False,
        decision='Proceed to next fixed gate' if r['qualified'] else 'Reject retained-pool fusion; keep deployed app and unused independent500. No outcome tuning.'))
    print(json.dumps({k:r[k] for k in ('before','after','paired','gates','display_changes','qualified')},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','inputs','run','report'])
    p.add_argument('--name',choices=KNOWN,default='calibration1450')
    p.add_argument('--part',type=int,choices=range(4))
    a=p.parse_args()
    if a.mode=='prepare':prepare()
    elif a.mode=='inputs':inputs(a.name,a.part)
    else:{'run':run,'report':report}[a.mode](a.name)
