package hk.cantonesemixeng.keyboard;
import java.io.*;
import java.util.*;
public class WordModeProbe {
    public static void main(String[] args)throws Exception {
        File assets=new File("app/src/main/assets");long start=System.nanoTime();
        DictionaryEngine dictionary=new DictionaryEngine(new FileReader(new File(assets,"cangjie5.base.dict.yaml")),
            new FileReader(new File(assets,"english.txt")),new FileReader(new File(assets,"character_frequencies.tsv")));
        WordLexicon words=new WordLexicon(dictionary,new FileReader(new File(assets,"quick_phrases.tsv")),new FileReader(new File(assets,"hk_phrases.tsv")),
            new FileReader(new File(assets,"cantonese_phrases.tsv")),new FileReader(new File(assets,"hk_chat_phrases.tsv")),new FileReader(new File(assets,"kinfx_words.tsv")));
        double startup=(System.nanoTime()-start)/1e6;
        List<String> codes=Arrays.asList("ofc","ofca","lwm","ofvd","ovoe","ovxe","yemm","haeu","ofykrmmsydwljpvwjd","dpofvivcjutrmyyjvcqnjd");
        for(String code:codes){List<InputCandidate> found=words.candidates(code,true,true,true,false,(c,w)->0);
            for(InputCandidate c:found)if(!code.startsWith(c.source)||(!c.englishOnly()&&dictionary.matchQuickCodes(c.source,c.text).isEmpty()
                    &&!dictionary.lookup(c.source,false,true,false).contains(c.text)))throw new AssertionError(code+":"+c.text);
            System.out.println(code+"="+found.stream().limit(3).map(c->c.text+"/"+c.source).toList());
        }
        for(int round=0;round<20;round++)for(String code:codes)for(int n=1;n<=code.length();n++)words.candidates(code.substring(0,n),true,true,true,false,(c,w)->0);
        List<Double> times=new ArrayList<>();int queries=0;
        for(int round=0;round<20;round++)for(String code:codes)for(int n=1;n<=code.length();n++){
            String prefix=code.substring(0,n);start=System.nanoTime();
            words.candidates(prefix,true,true,true,false,(c,w)->0);
            if(n>=3)words.captures(prefix,(c,w)->0);
            times.add((System.nanoTime()-start)/1e6);queries++;
        }
        Collections.sort(times);
        System.out.printf(Locale.ROOT,"words=%d startup_ms=%.1f queries=%d median_ms=%.3f p95_ms=%.3f max_ms=%.3f%n",words.size(),startup,queries,
            times.get(times.size()/2),times.get((int)(times.size()*.95)),times.get(times.size()-1));
    }
}
