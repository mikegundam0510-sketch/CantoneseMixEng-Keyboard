"""One fixed policy: the original first choice, then the neural relative tail."""
from visible_rerank_policy import quick_source as previous


def quick_source(text):
    text=previous(text)
    anchor='return VisibleCandidateReranker.rerank(result,finalScores,'
    if text.count(anchor)!=1:raise ValueError('Pinned-head anchor changed')
    return text.replace(anchor,'return PinnedHeadReranker.rerank(result,finalScores,')
