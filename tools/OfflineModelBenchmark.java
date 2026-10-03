import hk.kaiboard.android.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
public class OfflineModelBenchmark {
 static Reader a(String n)throws Exception{return new FileReader("src/main/assets/"+n);}
 public static void main(String[]args)throws Exception {
  DictionaryEngine d=new DictionaryEngine(a("cangjie5.base.dict.yaml"),a("english.txt"),a("character_frequencies.tsv"));
  QuickDecoder old=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"));
  QuickDecoder lm=new QuickDecoder(d,a("quick_phrases.tsv"),a("hk_phrases.tsv"),a("cantonese_phrases.tsv"),OfflineLanguageModel.load(new FileInputStream("src/main/assets/language_model.b64")));
  int[] hits=new int[4];long[] times=new long[120];int i=0;
  for(String line:Files.readAllLines(Path.of("../tools/lm_heldout_cases.tsv"))) {
   String[]f=line.split("\t",-1);List<String>b=old.decode(f[1],(c,w)->0,f[0]);
   long start=System.nanoTime();List<String>n=lm.decode(f[1],(c,w)->0,f[0]);times[i++]=System.nanoTime()-start;
   if(!b.isEmpty()&&b.get(0).equals(f[2]))hits[0]++;if(b.subList(0,Math.min(5,b.size())).contains(f[2]))hits[1]++;
   if(!n.isEmpty()&&n.get(0).equals(f[2]))hits[2]++;if(n.subList(0,Math.min(5,n.size())).contains(f[2]))hits[3]++;
  }
  Arrays.sort(times);System.out.println("heldout cases="+i+" old top1/top5="+hits[0]+"/"+hits[1]+" new top1/top5="+hits[2]+"/"+hits[3]+" decoder median/p95 ms="+times[60]/1e6+"/"+times[114]/1e6);
  for(String code:Arrays.asList("ofonaovrmrq","hionaovrmrq","ofspayemm","hisuvmjuisgehr","ofvdrf"))System.out.println(code+" "+lm.decode(code,(c,w)->0).subList(0,3));
 }
}
