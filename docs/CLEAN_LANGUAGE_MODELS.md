# Clean primary character and word models

This experiment follows the rejected short-feature residual in
[CLEAN_RANKING.md](CLEAN_RANKING.md). It changes the primary character/word model
training inputs while preserving production decoding, model strengths and
vocabulary. The baseline app is `b5b084fa043724f38913a8042b47ffcd551330e8`;
the parent main revision is `e31fed9`. No APK is generated.

## Before fitting

The pinned original HKCanCor ZIP, Rime Cantonese source, original lexical assets
from `5885daec1c43d676a525c543c8ab092532cb3150`, and frozen Tatoeba TRAIN data
reproduce **both production model files byte for byte** using the original
trainers. This verifies source identity rather than assuming current vocabulary
assets are the original model inputs. Their source hashes are in the manifest.

The new corpus contains25,177 original HK TRAIN spans (138,505 characters),
4,954 Tatoeba TRAIN spans (42,347 characters), and240 authored TRAIN examples
(2,304 characters). It uses all lengths and characters; the preceding ranking
experiment's cold-top24, length and colloquial-marker filters do not apply.
No keyboard characters or vocabulary tokens are removed.

Spaced English tokens such as `Mr Bean`, punctuation, digits and missing-speech
annotations end a Han span. Original HK word boundaries are retained inside each
span. Unparsed Han token syntax fails rather than silently discarding text.
Provenance stores the original source text, file/utterance or database record and
translation-family IDs, original code-point offsets, words and each change.

Unicode NFC and the same six reviewed OpenCC one-to-one glyph pairs are allowed.
Only five occurrences across five retained corpus rows change in this dataset.
Historical particles𡃉/𠻺/𠸏/𡁵 have no approved mapping and remain unchanged.
Editor text, evaluation answers and codes are untouched.

Only the original46 HK TRAIN conversations and frozen Tatoeba/authored TRAIN
families are admitted. Known evaluation overlap of six or more Han characters,
including normalized variants and joint reserve500, rejects14 HK spans and five
complete Tatoeba families. Historical TRAIN pair files are not mistaken for
evaluation inputs; this keeps all40 authored training families. Pinned external
lexical priors can naturally share words with evaluation sentences and are not
generated from evaluation labels.

The corpus, manifest and models are deterministic. Corpus attribution and
licences are in [NOTICE.md](../tools/data/clean_language_models/NOTICE.md).

## Frozen model and selection protocol

[protocol.json](../tools/data/clean_language_models/protocol.json) was written
before the first new fit or candidate decode. Exactly three ablations replace
the character model, word model, or both. There is no additional parameter grid.

The initial protocol is preserved as `protocol-initial.json`. A subsequent
non-predictive amendment fixes hexadecimal serialization of integer zero in
empty-text diagnostic fixtures (`float(score).hex()`). It changes no prediction,
training setting, case, candidate or gate. Original and amended source hashes
and fixed model hashes are recorded. Both the independent repeat fit and the
same fit under amended verification metadata produce identical model bytes.

Character training retains the interpolated5gram KLM2 format, thresholds and
production prior strength128. HK occurrences have weight12; a Tatoeba family
contributes each gram once at weight2. The original capped written priors and
Rime Cantonese weight2 are retained and normalized with the same reviewed rules.
No fitted token vocabulary is substituted into the decoder.

Word training retains the WLM1 bounded positive likelihood-ratio score,
production strength1, HK segmented-word observations and authored per-family
prior3. It uses word bigrams/trigrams, maximum12 characters and the strongest
relation per endpoint. Tatoeba has no verified word segmentation and is not
arbitrarily segmented for word training. Unknown relations remain neutral.

The known800 are observed calibration. New100 must preserve first/top5/top20;
old700 must preserve aggregate counts and per-set first/top5 losses must be
within one percentage point. At least first or top5 must improve overall.
Eligible models are selected by equal-set mean first, top5, top20, MRR, then
fixed priority character/word/combined. Candidate generation uses ordinary Java
inference with zero personal history and exact-code/unique20 checks.

Only a selected model proceeds to the old3,893 guard, actual Single32 learning,
Android checks and paired warmed same-JVM timing. Exact source/model hashes must
then be frozen before a single baseline/candidate pass on the independent500.
No post-reserve tuning is allowed. These incremental gates alone cannot support
a1.0 claim without the original major-gain and physical-device evidence.

## Calibration and learning checks

| Model replacement | First / top5 / top20 on known800 | Qualified |
| --- | --- | --- |
| Production baseline |171 /324 /421| Reference |
| Character only |172 /325 /423| Yes |
| Word only |171 /324 /421| No net gain |
| Both |172 /325 /423| Yes |

The selected arm is **character only**, following the fixed tie priority. New100
changes19/44/59→19/44/60; old700 changes152/280/362→153/281/363. This is only a
net gain of one first and one top5 hit on previously observed calibration800,
not a material independent accuracy claim. The word-only complete output lists
are compared separately; equal hit counts alone do not imply identical lists.

The selected model passes the existing actual Single32 simulation: three
explicit confirmations per sentence produce32/32 contextual first choices,
versus30/32 with the same legacy learning alone. This is retention of the
existing learning behavior, not evidence that this model improves personal
learning over production or survives an Android application update.

The selected character model passes the larger observed3,893 guard:
1,355/2,212/2,620→1,358/2,215/2,625 first/top5/top20. At first choice it gains five
cases and loses two (net+3); top5 gains six and loses three (net+3); top20 gains
seven and loses two (net+5). Per-set first/top5 losses remain within one
percentage point. These small, reused-set changes are not statistically strong
evidence of a population gain. Complete lists and per-set losses are retained.

## Independent decision and adoption

All29 focused Python checks and222 Android JVM tests pass. Android checks use
an isolated parent-main archive with the selected model, and create no APK.
Lint has no errors and the same25 warnings as the prior main report. Each of
the three ablations passes92 Python/Java score comparisons and504 token-split
checks, including empty text, punctuation, English, supplementary Han, cache
equivalence and exact word-score integration. Both20-case fresh baseline parity
samples match the cached outputs exactly.

Paired desktop timing alternates baseline/candidate order after30 warmup passes,
with11 samples per code and no other active Java workloads. All six wall/CPU
median ratios pass the1.2 limit; the largest ratio is1.0828. Some codes improve,
some slow down. This does not establish faster recognition on Fold7.

[`qualification.json`](../tools/data/clean_language_models/qualification.json)
freezes exact source, model, native class/asset and qualification-evidence hashes
before the first reserve decode. The selected character model and baseline each
run once on the previously unobserved500 words.hk examples. Start markers prevent
unrecorded repeats. This reserve is now **observed** and cannot serve as a new
independent comparison for later tuning.

| Independent500 | First | Top5 | Top20 |
| --- | ---: | ---: | ---: |
| Production baseline |107|179|235|
| Selected character model |107|180|236|

First ranks do not change. Top5 gains two cases and loses one, net+1; top20 also
gains two and loses one. The net top5 gain is0.2 percentage points, with no
statistically strong evidence of a population gain. These are public dictionary
examples, not contemporary private typing or physical-device measurements.

The frozen incremental gate passes, so **only `language_model.b64` is adopted**.
The word model, all vocabulary/dictionary assets, Java code, personal learning
storage, signing, Fold7 and0.6.39/code46 remain unchanged. New bundled
`PRIMARY_MODEL_REPORT.json` is authoritative for the current character model;
`MODEL_REPORT.json` is retained byte-identical as its historical baseline input
reference. Original model probability measurements do not describe the new
model. New OpenCC attribution/licence files accompany the transformed model.

No APK is produced and the1.0 major-gain/device gates are not reached. Merely
cleaning this older corpus has yielded a very small gain. A further experiment
should target substantially better sentence evidence with independently licensed
modern Cantonese data and a new untouched validation reserve; it must not use
these500 outcomes for answer-specific rules or call a repeated test independent.

## Reproduction

Activate `/workspace/android-environment/activate.sh` before Java commands.
Use the pinned original raw sources and original training assets, not current
expanded lexical tables. All output folders below must be fresh.

```sh
python3 tools/restore_clean_language_guards.py
python3 tools/train_clean_language_models.py prepare /path/hkcancor-utf8.zip /tmp/primary-corpus-replay
PYTHONPATH=tools python3 -m unittest test_joint_ranking test_structured_training test_clean_ranking test_clean_language_models
python3 tools/train_clean_language_models.py fit tools/data/clean_language_models \
  /path/jyut6ping3.words.dict.yaml /path/original-training-assets /tmp/primary-models
python3 tools/run_clean_language_models.py prepare /tmp/primary-native /tmp/primary-models
python3 tools/verify_clean_language_models.py /tmp/primary-native/combined /tmp/primary-scores.txt
python3 tools/run_clean_language_models.py run /tmp/primary-native character /tmp/primary-results/character.tsv
python3 tools/run_clean_language_models.py run /tmp/primary-native word /tmp/primary-results/word.tsv
python3 tools/run_clean_language_models.py run /tmp/primary-native combined /tmp/primary-results/combined.tsv
python3 tools/run_clean_language_models.py report /tmp/primary-native /tmp/primary-results /tmp/primary-selection.json
```

The full provenance unit check currently expects the raw ZIP at
`.native/search-alignment-20261014/hkcancor-utf8.zip`; provide the pinned file
there for that check. Source replay must reproduce corpus/manifest hashes.
Frozen sources and evaluation inputs are checked before fit and decode.
The guard-reference ZIP contains only previously observed3,893 cases and baseline
outputs; it restores the two byte-identical ignored cache files pinned by the
protocol. It neither evaluates a candidate nor contains the joint reserve500.

For the recorded guard pass, split the restored guard cases into four strided
shards (`rows[i::4]`), preserving their original order inside each shard. Decode
each with ordinary `native_phrase_relations.py run` on the selected archive;
`report_clean_language_guards.py` merges them in original order and validates
the complete lists and frozen guard. The archived guard JSON/TSV contains the
actual completed run. Single learning uses `ContextLearningEvaluation.java` on
`tools/hk_daily_context_cases.tsv`; paired timing uses
`PairedRankingPerformance` with warmup30/samples11. Candidate Android checks use
`testDebugUnitTest lintDebug` in the isolated archive, with pinned generated stroke
assets copied from the existing build inputs.

`evaluate_clean_language_reserve.py` documents the one-pass reserve procedure.
Its committed start markers intentionally prevent re-running the consumed
reserve as a new experiment. The complete two outputs, decision and paired
gain/loss report are archived; do not remove the markers or alter the frozen
qualification to retune after observing results.
