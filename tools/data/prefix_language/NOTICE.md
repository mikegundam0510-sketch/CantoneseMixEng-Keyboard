# Prefix-language TRAIN comparisons and research checkpoint

Derived actual TRAIN observations from the already attributed clean-ranking
data. Complete original notices remain in
[clean_ranking](../clean_ranking/NOTICE.md),
[current_search](../current_search/NOTICE.md) and
[sentence_pretrain](../sentence_pretrain/NOTICE.md).

HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), CC BY 4.0, original 46
TRAIN conversations. Tatoeba contributors via Aaron H. K. Tan / Jyut
Dictionary, snapshot 2023-04-08, CC BY 2.0 France, original TRAIN translation
families. UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
CC BY-SA 4.0, retained custom TRAIN subset. Project-authored scenarios are
synthetic supervision under the repository licence, not measured chat
frequency. Exact source revisions and full licence texts are linked from the
original notices and bundled app licences. Authors do not endorse modifications.

The adapted checkpoint starts from the attributed sentence-pretrain checkpoint,
including CC0 Common Voice Sentence Collector pretraining contributions. No
Common Voice raw or derived prompt text is mirrored here. New pairs contain
only existing admitted public TRAIN derivatives, never private phone text or
evaluation examples. Mixed derived pairs and checkpoint weights are offered
under CC BY-SA 4.0; original source contribution terms remain applicable.
Full CC BY-SA 4.0 terms are in
[`app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt`](../../../../app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt).
Code retains the repository code licence.

`pairs.jsonl.gz` records original family, domain, split, context, consumed code,
positive/negative actual prefixes, lost/survived origin, raw margin/rank and
original source identity. No gold path is injected or reconstructed. The
checkpoint uses original-family-disjoint internal validation only.

`reserve.tsv` and `reserve-source.jsonl` are words.hk public dictionary examples
under NCDOL 1.0, evaluation-only. Original attribution and full terms remain in
[`daily_prefix/NOTICE.txt`](../daily_prefix/NOTICE.txt) and
[`daily_prefix/LICENSE.txt`](../daily_prefix/LICENSE.txt). The pinned source
CSV hash, extraction rules, original text/headword families and exclusions are
retained. These examples never train a model or enter app assets. They are not
new independent speakers, private conversations or modern usage frequencies.
