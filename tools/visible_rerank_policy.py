"""Post-display scoring only; preserve original candidates and personal/mixed choices."""
from run_sentence_pretrain import source as early_source


def quick_source(text):
    value=early_source(text)
    early='''scores.put(path.text, path.score + sentenceRanker.score(context, path.text)
                    + (contextSentenceRanker==null?0:contextSentenceRanker.score(context,path.text)));'''
    if value.count(early)!=1:raise ValueError('Early model hook changed')
    value=value.replace(early,'scores.put(path.text, path.score + sentenceRanker.score(context, path.text));')
    signature='''    public List<String> decode(String input, ToIntBiFunction<String, String> learned, String context,
            ContextLearning.Preferences contextual) {'''
    if value.count(signature)!=1:raise ValueError('Decoder entry changed')
    value=value.replace(signature,signature+'''
        return decode(input,learned,context,contextual,true);
    }

    List<String> decodeBaseline(String input, ToIntBiFunction<String,String> learned, String context,
            ContextLearning.Preferences contextual) {
        return decode(input,learned,context,contextual,false);
    }

    private List<String> decode(String input, ToIntBiFunction<String,String> learned, String context,
            ContextLearning.Preferences contextual, boolean rerankVisible) {''')
    ending='''        if (result.size() > 20) return new ArrayList<>(result.subList(0, 20));
        return result;
    }

    /** Existing positive sentence relations'''
    replacement='''        if (result.size() > 20) result=new ArrayList<>(result.subList(0,20));
        if(!rerankVisible || contextSentenceRanker==null || finalScores==null
                || visiblePersonalPreference(code,context,result,learned,contextual)) return result;
        return VisibleCandidateReranker.rerank(result,finalScores,
            text -> contextSentenceRanker.score(context,text));
    }

    /** Whole-word decisions and confirmed/corrected context chains precede statistics. */
    private boolean visiblePersonalPreference(String code,String context,List<String> visible,
            ToIntBiFunction<String,String> learned,ContextLearning.Preferences contextual) {
        for(String text:visible) {
            if(knownWord(text) && learned.applyAsInt(code,text)!=0) return true;
            if(contextual==null) continue;
            InputCandidate candidate=InputCandidate.chinese(dictionary,code,text);
            if(ContextLearning.supports(context,candidate,contextual)) return true;
            String history=ContextLearning.tail(context);
            for(InputCandidate.Segment segment:candidate.segments) {
                if(!history.isEmpty() && contextual.weight(history,segment.code,segment.text)<0) return true;
                history=ContextLearning.tail(history+segment.text);
            }
        }
        return false;
    }

    /** Existing positive sentence relations'''
    if value.count(ending)!=1:raise ValueError('Display cutoff changed')
    return value.replace(ending,replacement)


def candidate_source(text):
    signature='''    public List<InputCandidate> chinese(String code, String context, boolean continuous, boolean useQuick,
            boolean useCangjie, ToIntBiFunction<String,String> learned,ContextLearning.Preferences contextual) {'''
    if text.count(signature)!=1:raise ValueError('Candidate entry changed')
    text=text.replace(signature,signature+'''
        return chineseInternal(code,context,continuous,useQuick,useCangjie,learned,contextual,true);
    }
    List<InputCandidate> chineseBaseline(String code,String context,boolean continuous,boolean useQuick,
            boolean useCangjie,ToIntBiFunction<String,String> learned,ContextLearning.Preferences contextual) {
        return chineseInternal(code,context,continuous,useQuick,useCangjie,learned,contextual,false);
    }
    private List<InputCandidate> chineseInternal(String code,String context,boolean continuous,boolean useQuick,
            boolean useCangjie,ToIntBiFunction<String,String> learned,ContextLearning.Preferences contextual,
            boolean rerankVisible) {''')
    call='for(String text:quick.decode(code,learned,context,contextual))'
    if text.count(call)!=1:raise ValueError('Candidate decode call changed')
    text=text.replace(call,'''for(String text:rerankVisible ? quick.decode(code,learned,context,contextual)
                    : quick.decodeBaseline(code,learned,context,contextual))''')
    call='List<InputCandidate> options=chinese(code,preceding,true,true,false,learned,contextual);'
    if text.count(call)!=1:raise ValueError('Mixed candidate call changed')
    return text.replace(call,'List<InputCandidate> options=chineseBaseline(code,preceding,true,true,false,learned,contextual);')


def translation_source(text):
    call='chinese.chinese(prefix,context,true,true,false,learned)'
    if text.count(call)!=1:raise ValueError('Translation prefix call changed')
    return text.replace(call,'chinese.chineseBaseline(prefix,context,true,true,false,learned,null)')
