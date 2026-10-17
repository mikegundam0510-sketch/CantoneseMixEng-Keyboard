"""Keep the closed visible-reranking policy; learn only its first-choice decision."""
from visible_rerank_policy import quick_source as visible_source


def quick_source(text):
    text=visible_source(text)
    anchor='''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        if (!Double.isFinite'''
    replacement='''                        SentenceLanguageRanker contextSentenceRanker) throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            clauseStartStrength,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,null);
    }
    public QuickDecoder(DictionaryEngine dictionary,Reader input,Reader hkInput,Reader cantoneseInput,
            OfflineLanguageModel model,PhraseLanguageModel phraseModel,Reader chatInput,
            CandidateRanker candidateRanker,CandidateRanker wordRanker,SentenceRanker sentenceRanker,
            PrefixRanker prefixRanker,PhraseRelationRanker relationRanker,SentenceLanguageRanker contextSentenceRanker,
            HeadChangeGate headChangeGate)throws IOException {
        this(dictionary,input,hkInput,cantoneseInput,model,phraseModel,chatInput,candidateRanker,wordRanker,
            CLAUSE_START_STRENGTH,sentenceRanker,prefixRanker,relationRanker,contextSentenceRanker,headChangeGate);
    }
    public QuickDecoder(DictionaryEngine dictionary,Reader input,Reader hkInput,Reader cantoneseInput,
            OfflineLanguageModel model,PhraseLanguageModel phraseModel,Reader chatInput,
            CandidateRanker candidateRanker,CandidateRanker wordRanker,double clauseStartStrength,SentenceRanker sentenceRanker,
            PrefixRanker prefixRanker,PhraseRelationRanker relationRanker,SentenceLanguageRanker contextSentenceRanker,
            HeadChangeGate headChangeGate)throws IOException {
        if (!Double.isFinite'''
    changes={anchor:replacement,
        '    private final SentenceLanguageRanker contextSentenceRanker;':
            '    private final SentenceLanguageRanker contextSentenceRanker;\n    private final HeadChangeGate headChangeGate;',
        'this.contextSentenceRanker=contextSentenceRanker;':
            'this.contextSentenceRanker=contextSentenceRanker;this.headChangeGate=headChangeGate;',
        'if(!rerankVisible || contextSentenceRanker==null || finalScores==null':
            'if(!rerankVisible || contextSentenceRanker==null || headChangeGate==null || finalScores==null',
        '''return VisibleCandidateReranker.rerank(result,finalScores,
            text -> contextSentenceRanker.score(context,text));''':
            '''return HeadChangeGate.rerank(result,finalScores,
            text -> contextSentenceRanker.score(context,text),text -> structuralSupport(context,text),headChangeGate);'''}
    for old,new in changes.items():
        if text.count(old)!=1:raise ValueError('Head gate integration changed: '+old[:70])
        text=text.replace(old,new)
    return text
