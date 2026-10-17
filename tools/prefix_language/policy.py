"""One bounded prefix-rescue policy; original scores and final gates remain."""
RESERVE = '''
    private List<Path> prune(List<Path> input,String context,List<Token> following,ModelScoreCache scores) {
        List<Path> result=pruneExisting(input,context,following,scores);
        if(scores==null||scores.prefixSession==null||result.size()<BEAM||input.size()<=result.size()
                ||!scores.prefixSession.available())return result;
        SearchLanguageRanker.Session session=scores.prefixSession;
        Path boundary=result.get(BEAM-1);double floor=boundary.score-4;
        Set<String> seen=new HashSet<>(),histories=new HashSet<>();
        for(Path p:result){seen.add(p.text);histories.add(PrefixRanker.tail(context+p.text));}
        List<Path> raw=new ArrayList<>(input);
        raw.sort(Comparator.comparingDouble((Path p)->p.score).reversed().thenComparing(p->p.text));
        double reference=session.score(boundary.text);if(!Double.isFinite(reference))return result;
        List<Path> proposals=new ArrayList<>();Map<Path,Double> evidence=new IdentityHashMap<>();
        Set<String> inspected=new HashSet<>();int checked=0;
        for(Path p:raw) {
            if(p.score<floor)break;
            if(seen.contains(p.text)||!inspected.add(PrefixRanker.tail(context+p.text)))continue;
            if(checked++==8||!session.available())break;
            double value=session.score(p.text)-reference;
            if(Double.isFinite(value)&&value>.25){proposals.add(p);evidence.put(p,p.score+value);}
        }
        proposals.sort(Comparator.comparingDouble((Path p)->evidence.get(p)).reversed().thenComparing(p->p.text));
        int added=0;
        for(Path p:proposals)if(histories.add(PrefixRanker.tail(context+p.text))) {
            result.add(p);if(++added==4)break;
        }
        return result;
    }
'''


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Changed prefix-language anchor: '+old[:90])
    return text.replace(old, new)


def source(text):
    text=once(text,'    private final SentenceLanguageRanker contextSentenceRanker;',
        '    private final SentenceLanguageRanker contextSentenceRanker;\n    private final SearchLanguageRanker searchLanguageRanker;')
    anchor='''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        if (!Double.isFinite(clauseStartStrength)'''
    replacement='''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,null);
    }
    public QuickDecoder(DictionaryEngine dictionary, Reader input, Reader hkInput, Reader cantoneseInput,
                        OfflineLanguageModel model, PhraseLanguageModel phraseModel, Reader chatInput,
                        CandidateRanker candidateRanker, CandidateRanker wordRanker, double clauseStartStrength,
                        SentenceRanker sentenceRanker, PrefixRanker prefixRanker, PhraseRelationRanker relationRanker,
                        SentenceLanguageRanker contextSentenceRanker,SearchLanguageRanker searchLanguageRanker) throws IOException {
        if (!Double.isFinite(clauseStartStrength)'''
    text=once(text,anchor,replacement)
    text=once(text,'        this.prefixRanker = prefixRanker;',
        '        this.prefixRanker = prefixRanker;this.searchLanguageRanker=searchLanguageRanker;')
    text=once(text,'    private final class ModelScoreCache {','''    private final class ModelScoreCache {
        final SearchLanguageRanker.Session prefixSession;
        ModelScoreCache(String context,boolean enabled) {
            prefixSession=enabled&&searchLanguageRanker!=null?searchLanguageRanker.session(context):null;
        }''')
    text=once(text,'new ModelScoreCache();','new ModelScoreCache(context,rerankVisible);')
    anchor='    private List<Path> prune(List<Path> input, String context, List<Token> following, ModelScoreCache modelScores) {'
    text=once(text,anchor,RESERVE+'\n'+anchor.replace('prune(', 'pruneExisting('))
    return text
