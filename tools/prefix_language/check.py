"""Reference parity, neutral fallback and observer-answer isolation on TRAIN."""
import subprocess
from experiment import DATA,WORK,REPORTS,driver,write,frozen,ROOT


def main():
    frozen();w=WORK/'preflight';w.mkdir(exist_ok=True)
    rows=(DATA/'observation-cases.tsv').read_text().splitlines()[:5]
    cases=w/'cases.tsv';cases.write_text(''.join(r+'\n' for r in rows))
    changed=w/'changed-input.tsv';changed.write_text(''.join('\t'.join(r.split('\t')[:3]+['甲乙'])+'\n' for r in rows))
    q=WORK/'language';text=driver(True).replace('class RelationEvaluation','class PrefixNullEvaluation')
    text=text.replace('Files.exists(assets.resolve("search_language.b64"))?SearchLanguageRanker.load(Files.newInputStream(assets.resolve("search_language.b64"))):null','null')
    p=q/'PrefixNullEvaluation.java';p.write_text(text)
    tests=[p,ROOT/'tools/prefix_language/PrefixSessionCheck.java',ROOT/'tools/prefix_language/PrefixReserveCheck.java']
    subprocess.run(['javac','-encoding','UTF-8','-cp',str(q/'classes'),'-d',str(q/'classes')]+list(map(str,tests)),check=True)
    for name,out,args in [('PrefixSessionCheck','session-check.txt',[ROOT/'app/src/main/assets/sentence_language.b64']),('PrefixReserveCheck','reserve-check.txt',[])]:
        r=subprocess.run(['java','-cp',str(q/'classes'),'hk.cantonesemixeng.keyboard.'+name]+list(map(str,args)),capture_output=True,text=True,check=True)
        (REPORTS/out).write_text(r.stdout)
    def run(stage,name,inputs,out,extra=[]):
        if inputs.resolve()==out.resolve():raise ValueError('Input/output collision')
        subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.'+name,str(stage/'app/src/main/assets'),str(inputs),str(out)]+list(map(str,extra)),check=True)
    run(WORK/'baseline','RelationEvaluation',cases,w/'before.tsv')
    run(q,'PrefixNullEvaluation',cases,w/'null.tsv')
    run(WORK/'observer','RelationEvaluation',cases,w/'observed.tsv',[w/'prefix.tsv'])
    run(WORK/'observer','RelationEvaluation',changed,w/'changed-output.tsv',[w/'changed-prefix.tsv'])
    assert (w/'before.tsv').read_bytes()==(w/'null.tsv').read_bytes()==(w/'observed.tsv').read_bytes()
    assert [r.split('\t')[5] for r in (w/'before.tsv').read_text().splitlines()]==[r.split('\t')[5] for r in (w/'changed-output.tsv').read_text().splitlines()]
    write(REPORTS/'preflight.json',dict(score_prefix_reference_cases=340,live_prune_rescue=True,original48_preserved_at_each_rescue=True,
        query_budget=128,state_budget=2048,neutral_and_disabled_bypass=True,ordinary_parent_null_and_observer_parity_cases=5,
        changing_observer_answers_changes_no_candidates=True,not_accuracy_evidence=True))
    print('preflight_parity5=true answer_isolation5=true')


if __name__=='__main__':main()
