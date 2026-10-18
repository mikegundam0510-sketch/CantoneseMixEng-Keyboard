# TRAIN-supported vocabulary expansion research

Code retains the repository GPL-3.0-or-later licence. The expanded weights are
modified derivatives of the frozen teacher model in
[`../code_generator/`](../code_generator/NOTICE.md), offered under CC BY-SA4.0.
Full terms remain bundled at
[`licenses/sentence-language/CC-BY-SA-4.0.txt`](../../../app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt).
All previous source contributions, dictionary licences and attributions remain.

HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), CC BY4.0, original TRAIN
conversation split. Tatoeba contributors via Aaron H. K. Tan/Jyut Dictionary,
2023-04-08 snapshot, CC BY2.0 France. UD Cantonese-HK: Tak-sum Wong, Kim Gerdes,
Herman Leung and John Lee (Depling2017), CC BY-SA4.0. Mozilla Common Voice
Sentence Collector contributors donated read prompts under CC0. Project-authored
examples are synthetic. These are not measured private typing frequencies.
Complete source URLs, pinned revisions, term hashes and original split definitions
remain in [`../sentence_pretrain/NOTICE.md`](../sentence_pretrain/NOTICE.md),
[`source-audit.json`](../sentence_pretrain/source-audit.json) and linked notices.
Authors do not endorse these modifications.

The old model's2248 rows and shared weights are retained bit-identically.
Only245 added character embedding/output rows are fitted. Public artifacts
contain aggregate character support, legal dictionary code facts, hashes and
weights. Raw/derived Common Voice prompt views remain in ignored local caches;
they are not mirrored in Git or the app. No phone learning records are collected.

New independent examples are frozen public reviewed words.hk dictionary examples,
Hong Kong Lexicography Limited, NCDOL1.0. They are evaluation-only, never fitted or
packaged. Preserve the attribution and full terms in
[`../daily_prefix/NOTICE.txt`](../daily_prefix/NOTICE.txt) and
[`../daily_prefix/LICENSE.txt`](../daily_prefix/LICENSE.txt).
The previous two500 sets are already observed; this new500 remains undecoded
because an earlier known regression gate failed. This experiment is not adopted.
