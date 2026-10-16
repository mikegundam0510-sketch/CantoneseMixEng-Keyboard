# Recurrent context-scoring experiment

This is a modified derivative of the already attributed clean TRAIN final
comparisons, not a new private message corpus. Complete credits and licences
remain in [clean_ranking/NOTICE.md](../clean_ranking/NOTICE.md) and its original
linked source notices:

- HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), CC BY4.0, original TRAIN
  conversations only. Corpus words/spans are retained with the prior provenance.
- Tatoeba contributors via Aaron H. K. Tan's Jyut Dictionary, snapshot2023-04-08,
  CC BY2.0 France, frozen TRAIN translation families only.
- UD_Cantonese-HK: Wong, Gerdes, Leung and Lee, CC BY-SA4.0, the original custom
  TRAIN subset; no evaluation productions fit this model.
- Project-authored training families, including daily templates: repository
  licence, synthetic priorities rather than measured usage frequencies.
- Candidate text/vocabulary contributions retain their original Rime and other
  source notices in [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md).

`pairs.jsonl.gz` retains family, context, exact code, positive/negative strings,
clipped historical margin, domain and an internal family-disjoint split. It is
derived only from final comparisons in the pinned clean TRAIN pair source.
No prefix reconstruction is injected into actual inference. Source families,
cases and rivals receive normalized mass rather than duplicate frequency credit.

The two research assets contain a small character embedding/reset-after GRU
whole-candidate residual, offered as modified statistical data under CC BY-SA4.0.
Source contribution licences remain applicable; source authors do not endorse
these modifications. Model code remains under the repository code licence.
NumPy2.3.5 is used for offline fitting; no external neural framework is required
by the Java scorer or bundled with Android. All arrays and editor-context states
are local; no phone text or personal learning records are collected.

words.hk NCDOL1.0 examples are **evaluation-only**. They never train this model,
enter its embedding vocabulary, or ship in an APK. The new500 reserve belongs to
the preceding context-search data; it is not decoded unless qualification passes.
Model capacity and training losses do not establish keyboard accuracy.
