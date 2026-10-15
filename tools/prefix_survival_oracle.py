#!/usr/bin/env python3
"""Gold-assisted survival intervention, archive-only; never an inference candidate.

Append at most one already generated, exactly continuable gold prefix after each
ordinary prune. Option generation, completed-path cuts, confidence and ranking
remain unchanged. This intervention uses the answer; it is neither deployable
accuracy nor a formal maximum over tokenizations, option generation and ranking.
"""
import argparse
import io
from pathlib import Path
import subprocess
import tarfile
from native_phrase_relations import DRIVER
from train_phrase_model import ROOT

HOOK=r'''
    static String oracleGold="",oracleCode="";
    static int oraclePosition,oracleAdded;
    static boolean oracleEnabled=true;
    static boolean oracleGenerated,oracleCompleted,oracleEligible;
    private List<Path> prune(List<Path> input,String context,List<Token> following,ModelScoreCache cache) {
        List<Path> result=ordinaryPrune(input,context,following,cache);
        if(!oracleEnabled||oraclePosition<=0||oraclePosition>=oracleCode.length())return result;
        for(Path path:result)if(oracleGold.startsWith(path.text)
            &&!dictionary.matchQuickCodes(oracleCode.substring(oraclePosition),oracleGold.substring(path.text.length())).isEmpty())return result;
        Path best=null;
        for(Path path:input)if(oracleGold.startsWith(path.text)
            &&!dictionary.matchQuickCodes(oracleCode.substring(oraclePosition),oracleGold.substring(path.text.length())).isEmpty()
            &&(best==null||path.score>best.score))best=path;
        if(best!=null){result.add(best);oracleAdded++;}
        return result;
    }
'''

def instrument(source):
    changes={
        '    private static final int BEAM = 48;':HOOK+'\n    private static final int BEAM = 48;',
        '    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {':
        '    private List<Path> ordinaryPrune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {',
        '            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);':
        '            oraclePosition=pos;\n            List<Path> paths = prune(lattice.get(pos), context, following.get(pos), modelScores);',
        '                if (target.size() > 1024) lattice.set(pos + length,':
        '                if (target.size() > 1024) { oraclePosition=pos+length; lattice.set(pos + length,',
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores));':
        '? pruneFinal(target) : prune(target, context, following.get(pos + length), modelScores)); }',
        'target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));':
        '''if(pos+length==code.length()&&(prefix.text+choice.getKey()).equals(oracleGold))oracleGenerated=true;
                        target.add(new Path(prefix.text + choice.getKey(), prefix.score + score + wordBonus + bonus));''',
        '        List<Path> completed = pruneFinal(lattice.get(code.length()));':
        '''        List<Path> completed = pruneFinal(lattice.get(code.length()));
        for(Path path:completed)if(path.text.equals(oracleGold)){oracleCompleted=true;oracleGenerated=true;}''',
        '        Map<String,Double> finalScores=null;':
        '        oracleEligible=result.contains(oracleGold);\n        Map<String,Double> finalScores=null;',
    }
    for before,after in changes.items():
        if source.count(before)!=1:raise ValueError('Oracle hook changed: '+before)
        source=source.replace(before,after)
    return source

def run(cases,output,work,revision,enabled=True):
    revision=subprocess.check_output(['git','rev-parse','--verify',revision+'^{commit}'],cwd=ROOT,text=True).strip()
    work.mkdir(parents=True,exist_ok=True)
    archive=subprocess.check_output(['git','archive',revision,'app/src/main/java','app/src/main/assets'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as data:data.extractall(work,filter='data')
    engine=work/'app/src/main/java/hk/cantonesemixeng/keyboard/QuickDecoder.java'
    engine.write_text(instrument(engine.read_text()))
    driver=DRIVER.replace('public class RelationEvaluation','public class PrefixOracleEvaluation')
    driver=driver.replace('assets=Path.of(args[0]);',
        'assets=Path.of(args[0]);QuickDecoder.oracleEnabled='+str(enabled).lower()+';')
    driver=driver.replace('List<String> values=q.decode(f[2],',
        '''QuickDecoder.oracleGold=f[3];QuickDecoder.oracleCode=f[2];QuickDecoder.oracleAdded=0;
    QuickDecoder.oracleGenerated=false;QuickDecoder.oracleCompleted=false;QuickDecoder.oracleEligible=false;
    List<String> values=q.decode(f[2],''')
    driver=driver.replace('int count=0;try(',
        'long additions=0;int intervened=0;int count=0;try(')
    driver=driver.replace('if(++count%100==0)',
        'additions+=QuickDecoder.oracleAdded;if(QuickDecoder.oracleAdded>0)intervened++;if(++count%100==0)')
    driver=driver.replace('try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2])))',
        'try(BufferedWriter out=Files.newBufferedWriter(Path.of(args[2]));BufferedWriter diag=Files.newBufferedWriter(Path.of(args[3])))')
    driver=driver.replace('additions+=QuickDecoder.oracleAdded;',
        '''diag.write(line+"\\t"+QuickDecoder.oracleAdded+"\\t"+QuickDecoder.oracleGenerated+"\\t"
        +QuickDecoder.oracleCompleted+"\\t"+QuickDecoder.oracleEligible+"\\n");
    additions+=QuickDecoder.oracleAdded;''')
    driver=driver.replace('\n  }\n }\n}',
        '\n  }\n  System.out.println("ORACLE gold-assisted cases="+count+" intervened="+intervened+" added="+additions);\n }\n}')
    java=work/'PrefixOracleEvaluation.java';java.write_text(driver)
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(work/'app/src/main/java'),'-d',str(work/'classes'),str(java)],check=True)
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True);pending=output.with_suffix('.pending.tsv')
    diagnostic=output.with_suffix('.diagnostics.tsv');diagnostic_pending=output.with_suffix('.diagnostics.pending.tsv')
    subprocess.run(['java','-Xmx1g','-cp',str(work/'classes'),'hk.cantonesemixeng.keyboard.PrefixOracleEvaluation',
                    str(work/'app/src/main/assets'),str(cases.resolve()),str(pending),str(diagnostic_pending)],check=True)
    diagnostic_pending.replace(diagnostic)
    pending.replace(output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','output','work'):p.add_argument(name,type=Path)
    p.add_argument('--revision',default='d8575595b689916d8649e71e1a365224392683a9')
    p.add_argument('--control',action='store_true',help='Disable intervention to verify native baseline parity')
    a=p.parse_args();run(a.cases,a.output,a.work,a.revision,not a.control)
