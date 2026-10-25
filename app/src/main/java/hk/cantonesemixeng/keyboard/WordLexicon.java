package hk.cantonesemixeng.keyboard;

import java.io.*;
import java.util.*;
import java.util.function.ToIntBiFunction;
import java.util.function.ToIntFunction;

/** Attested words only; matches every native Quick alias without expanding their Cartesian product. */
final class WordLexicon {
    private final DictionaryEngine dictionary;
    private final Map<String,Word> words=new HashMap<>();
    private final Map<Integer,List<Word>> starts=new HashMap<>(), associations=new HashMap<>();
    private static final class Word {
        final String text; final double frequency; final int[][] aliases;
        Word(String text,double frequency,int[][] aliases){this.text=text;this.frequency=frequency;this.aliases=aliases;}
    }
    private static final class Match {
        final InputCandidate candidate;final double frequency;
        Match(InputCandidate candidate,double frequency){this.candidate=candidate;this.frequency=frequency;}
    }
    WordLexicon(DictionaryEngine dictionary,Reader... sources)throws IOException {
        this.dictionary=dictionary;Map<String,Double> frequencies=new HashMap<>();
        for(Reader source:sources)if(source!=null)try(BufferedReader in=new BufferedReader(source)) {
            String line;while((line=in.readLine())!=null) {
                if(line.isEmpty()||line.startsWith("#"))continue;
                String[] f=line.split("\t");if(f.length<2)continue;
                String text=f.length==2?f[0]:f[1],raw=f.length==2?f[1]:f[2];
                int size=text.codePointCount(0,text.length());
                if(size<2||size>8||!QuickDecoder.hanText(text))continue;
                try {double count=Double.parseDouble(raw);if(Double.isFinite(count)&&count>0)frequencies.merge(text,count,Math::max);}
                catch(NumberFormatException malformed){throw new IOException("Invalid word frequency",malformed);}
            }
        }
        Map<Integer,int[]> cache=new HashMap<>();
        List<String> ordered=new ArrayList<>(frequencies.keySet());Collections.sort(ordered);
        for(String text:ordered) {
            int[] cps=text.codePoints().toArray();int[][] aliases=new int[cps.length][];boolean supported=true;
            for(int i=0;i<cps.length;i++) {
                final int cp=cps[i];
                aliases[i]=cache.computeIfAbsent(cp,k->dictionary.quickCodesFor(new String(Character.toChars(cp))).stream()
                    .filter(code->code.matches("[a-z]{1,2}")).mapToInt(WordLexicon::id).sorted().distinct().toArray());
                if(aliases[i].length==0){supported=false;break;}
            }
            if(!supported)continue;
            Word word=new Word(text,frequencies.get(text),aliases);words.put(text,word);
            for(int key:aliases[0])starts.computeIfAbsent(key,k->new ArrayList<>()).add(word);
            associations.computeIfAbsent(cps[0],k->new ArrayList<>()).add(word);
        }
    }
    private static int id(String code){return code.length()==1?code.charAt(0)-'a':26+26*(code.charAt(0)-'a')+code.charAt(1)-'a';}
    boolean knownWord(String text){return words.containsKey(text);}
    int size(){return words.size();}

    private int matchedKeys(String input,Word word) {
        long positions=1L;
        for(int[] aliases:word.aliases) {
            long next=0;
            while(positions!=0) {
                int p=Long.numberOfTrailingZeros(positions);positions&=positions-1;
                if(p<input.length() && Arrays.binarySearch(aliases,input.charAt(p)-'a')>=0)next|=1L<<(p+1);
                if(p+1<input.length() && Arrays.binarySearch(aliases,26+26*(input.charAt(p)-'a')+input.charAt(p+1)-'a')>=0)next|=1L<<(p+2);
            }
            positions=next;if(positions==0)return 0;
        }
        return 63-Long.numberOfLeadingZeros(positions);
    }

    List<InputCandidate> candidates(String raw,boolean quick,boolean cangjie,boolean continuous,
            boolean singlesOnly,ToIntBiFunction<String,String> usage) {
        if(raw==null||!raw.matches("[a-zA-Z]{1,48}"))return Collections.emptyList();
        String input=raw.toLowerCase(Locale.ROOT);
        Map<Integer,LinkedHashMap<String,Match>> groups=new TreeMap<>(Comparator.reverseOrder());
        for(String text:dictionary.lookup(input,quick,cangjie,false))if(!text.equals(input))
            put(groups,InputCandidate.chinese(dictionary,raw,text),dictionary.frequency(text));
        if(quick&&continuous&&input.length()>2) {
            if(!singlesOnly) {
                Set<Word> seen=new HashSet<>();
                for(int length=1;length<=2;length++)for(Word word:starts.getOrDefault(id(input.substring(0,length)),Collections.emptyList())) {
                    if(!seen.add(word))continue;
                    int consumed=matchedKeys(input,word);
                    if(consumed>=3)put(groups,InputCandidate.chinese(dictionary,raw.substring(0,consumed),word.text),word.frequency);
                }
            } else groups.clear();
            for(int length=2;length>=1;length--) {
                String prefix=raw.substring(0,length);
                for(String text:dictionary.quickCandidates(prefix))put(groups,InputCandidate.chinese(dictionary,prefix,text),dictionary.frequency(text));
            }
        }
        List<InputCandidate> result=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(LinkedHashMap<String,Match> group:groups.values()) {
            List<Match> ranked=new ArrayList<>(group.values());
            ranked.sort(Comparator.comparingInt((Match m)->usage.applyAsInt(m.candidate.effectiveCode(),m.candidate.text)).reversed()
                .thenComparing(Comparator.comparingInt((Match m)->knownWord(m.candidate.text)?1:0).reversed())
                .thenComparing(Comparator.comparingDouble((Match m)->m.frequency).reversed()));
            for(Match match:ranked)if(seen.add(match.candidate.text))result.add(match.candidate);
        }
        return result;
    }
    private void put(Map<Integer,LinkedHashMap<String,Match>> groups,InputCandidate value,double frequency) {
        groups.computeIfAbsent(value.source.length(),k->new LinkedHashMap<>()).putIfAbsent(value.text,new Match(value,frequency));
    }

    /** Used by optional third-key top-out; only hot or personally selected words hold keys. */
    boolean captures(String raw,ToIntBiFunction<String,String> usage) {
        if(raw==null||!raw.matches("[a-zA-Z]{3,48}"))return false;
        String input=raw.toLowerCase(Locale.ROOT);Set<Word> seen=new HashSet<>();
        for(int length=1;length<=2;length++)for(Word word:starts.getOrDefault(id(input.substring(0,length)),Collections.emptyList())) {
            if(!seen.add(word))continue;
            if(input.length()<=4 && word.frequency<19000 && !(input.length()>=3 && word.frequency>=3000 && matchedKeys(input,word)==input.length())
                    && !selectedWordPrefix(input,word,usage))continue;
            if(hasCodePrefix(input,word))return true;
        }
        return false;
    }
    private boolean selectedWordPrefix(String input,Word word,ToIntBiFunction<String,String> usage) {
        // Complete learned spelling, when available; a partial spelling has no
        // independent frequency and must not invent a selected-word record.
        int used=matchedKeys(input,word);
        return used==input.length() && usage.applyAsInt(input,word.text)>0;
    }
    private boolean hasCodePrefix(String input,Word word) {
        long positions=1;
        for(int[] aliases:word.aliases) {
            long next=0;
            while(positions!=0) {
                int p=Long.numberOfTrailingZeros(positions);positions&=positions-1;
                if(p==input.length())return true;
                if(Arrays.binarySearch(aliases,input.charAt(p)-'a')>=0)next|=1L<<(p+1);
                if(p+1<input.length()) {
                    if(Arrays.binarySearch(aliases,26+26*(input.charAt(p)-'a')+input.charAt(p+1)-'a')>=0)next|=1L<<(p+2);
                } else for(int key:aliases)if(key>=26 && (key-26)/26==input.charAt(p)-'a')return true;
            }
            positions=next;if(positions==0)return false;
        }
        return (positions&(1L<<input.length()))!=0;
    }

    List<String> nextSuggestions(String context,int limit,ToIntFunction<String> usage) {
        if(context==null||context.isEmpty()||limit<=0)return Collections.emptyList();
        int[] history=context.codePoints().toArray();Map<String,Double> scores=new HashMap<>();
        for(int length=Math.min(7,history.length);length>=1;length--) {
            String prefix=new String(history,history.length-length,length);
            if(!QuickDecoder.hanText(prefix))continue;
            for(Word word:associations.getOrDefault(prefix.codePointAt(0),Collections.emptyList())) {
                if(!word.text.startsWith(prefix)||word.text.length()==prefix.length())continue;
                String tail=word.text.substring(prefix.length());
                scores.merge(tail,length*1000000.0+Math.max(-100000,Math.min(100000,usage.applyAsInt(word.text)))*5+Math.log1p(word.frequency),Math::max);
            }
        }
        List<String> values=new ArrayList<>(scores.keySet());
        values.sort(Comparator.comparingDouble((String text)->scores.get(text)).reversed().thenComparing(text->text));
        return new ArrayList<>(values.subList(0,Math.min(limit,values.size())));
    }
}
