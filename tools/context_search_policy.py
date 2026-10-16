"""Fixed-budget experimental search policies; no label or training features."""
PREFIX=r'''
    /** Keep high-ranked paths and distinct future histories within the same48 slots. */
    private List<Path> distinctPaths(List<Path> input) {
        List<Path> ranked=new ArrayList<>();Set<String> unique=new HashSet<>();
        for(Path p:input)if(unique.add(p.text))ranked.add(p);
        if(model==null||ranked.size()<=BEAM)return new ArrayList<>(ranked.subList(0,Math.min(BEAM,ranked.size())));
        final int protectedHeads=__HEADS__;
        double floor=ranked.get(BEAM-1).score-4;
        Set<String> seen=new HashSet<>(),histories=new HashSet<>();
        List<Path> result=new ArrayList<>(ranked.subList(0,protectedHeads));
        Map<Path,Integer> order=new IdentityHashMap<>();
        for(int i=0;i<ranked.size();i++)order.put(ranked.get(i),i);
        for(Path p:result){seen.add(p.text);histories.add(searchHistory(p.text));}
        for(int i=protectedHeads;i<ranked.size()&&result.size()<BEAM;i++) {
            Path p=ranked.get(i);
            if(p.score>=floor&&histories.add(searchHistory(p.text))){result.add(p);seen.add(p.text);}
        }
        for(Path p:ranked)if(result.size()<BEAM&&seen.add(p.text))result.add(p);
        result.sort(Comparator.comparingInt(order::get));
        return result;
    }
    private static String searchHistory(String text) {
        int count=text.codePointCount(0,text.length());
        return text.substring(text.offsetByCodePoints(0,Math.max(0,count-4)));
    }
'''

COMPLETED=r'''
    /** Existing sentence evidence can protect a complete path before the raw cutoff. */
    private List<Path> pruneFinal(List<Path> input,String context) {
        if(model==null||sentenceRanker==null)return prune(input);
        input.sort(Comparator.comparingDouble((Path p)->p.score).reversed());
        List<Path> ranked=new ArrayList<>();Set<String> seen=new HashSet<>();
        for(Path p:input)if(seen.add(p.text)){ranked.add(p);if(ranked.size()==2*finalPool)break;}
        if(ranked.size()<=finalPool)return ranked;
        int protectedHeads=finalPool-32;
        List<Path> result=new ArrayList<>(ranked.subList(0,protectedHeads));
        Set<Path> selected=Collections.newSetFromMap(new IdentityHashMap<>());selected.addAll(result);
        Map<Path,Integer> order=new IdentityHashMap<>();
        for(int i=0;i<ranked.size();i++)order.put(ranked.get(i),i);
        Map<Path,Double> scores=new IdentityHashMap<>();
        List<Path> proposals=new ArrayList<>(ranked.subList(protectedHeads,ranked.size()));
        for(Path p:proposals)scores.put(p,p.score+sentenceRanker.score(context,p.text));
        proposals.sort(Comparator.comparingDouble((Path p)->scores.get(p)).reversed()
            .thenComparingInt(order::get));
        for(Path p:proposals)if(result.size()<finalPool&&selected.add(p))result.add(p);
        result.sort(Comparator.comparingInt(order::get));
        return result;
    }
'''

ARMS={'prefix40':(40,False),'prefix32':(32,False),'completed':(0,True),'combined':(40,True)}


def source(text,arm):
    heads,completed=ARMS[arm]
    if heads:
        start=text.index('    private static List<Path> distinctPaths(List<Path> input) {')
        end=text.index('\n    }',start)+6
        text=text[:start]+PREFIX.replace('__HEADS__',str(heads)).rstrip()+text[end:]
        text=text.replace('    private static List<Path> prune(List<Path> input) {','    private List<Path> prune(List<Path> input) {')
    if completed:
        start=text.index('    private List<Path> pruneFinal(List<Path> input) {')
        end=text.index('\n    }',start)+6
        text=text[:start]+COMPLETED.rstrip()+text[end:]
        assert text.count('pruneFinal(target)')==1 and text.count('pruneFinal(lattice.get(code.length()))')==1
        text=text.replace('pruneFinal(target)','pruneFinal(target,context)')
        text=text.replace('pruneFinal(lattice.get(code.length()))','pruneFinal(lattice.get(code.length()),context)')
    return text
