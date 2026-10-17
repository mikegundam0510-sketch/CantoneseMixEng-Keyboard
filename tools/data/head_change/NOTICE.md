# First-choice decision model

The new gate uses only numeric scores/structure from the existing admitted
HKCanCor, Tatoeba, UD and project-authored TRAIN candidates. Original conversation,
translation and scenario attribution and source licences continue to apply;
see [sentence_pretrain/NOTICE.md](../sentence_pretrain/NOTICE.md) and
[current_search/NOTICE.md](../current_search/NOTICE.md).

The derived gate weights are provided under CC BY-SA4.0; repository code retains
its existing code licence. The unchanged neural checkpoint also retains its
Common Voice CC0/source notices. No Common Voice prompt text, raw or derived
corpus, phone messages, accounts or personal learning records are copied here.
Numeric-feature caches remain in ignored `.native`.

words.hk/NCDOL examples remain evaluation-only. The previously used1,450 and3,893
cases are calibration/guards; neither is a fresh real-user accuracy study.
