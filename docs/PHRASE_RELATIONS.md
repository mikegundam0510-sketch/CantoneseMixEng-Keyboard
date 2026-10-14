# Hong Kong natural examples and phrase relations (unreleased)

This implements two changes: expanding actual Hong Kong same-code training
competitors, and scoring word-level subject/action/object, negation, classifier
and question relations. Baseline is the fixed `21ede20` source and assets; it is
not a claim that the currently installed APK0.6.39 has all these source changes.
The independent trial does **not** improve first/top5 hits. The code and training
artifacts are retained, but `relation_ranker.b64` is absent from app assets and
the optional service loader falls back to the unchanged candidate order.

## Frozen data and source boundaries

Training grows from3,081 to5,381 rows, adding2,000 eligible full HKCanCor chunks
and300 manually annotated Cantonese dialogue/interview chunks. Existing HKCanCor
training/excluded conversation boundaries remain intact. The added HKCanCor text
was available to the old language model; it is newly sampled for pairwise error
training. The UD productions are genuinely additional sources, with a custom
source split: two productions train, a third validates, parliament tests.

The5,610-entry POS lexicon uses only training-source word boundaries and tags.
It never reads validation/test tags. The new143 calibration cases comprise100
dictionary examples and43 unused film utterances. They join the existing660
known cases for803-case tuning. The unused796-case reserve comprises500 fresh
dictionary source families and296 parliament utterances, at most one eligible
chunk per original treebank sentence. It is opened only after selection and
regression checks.

Known evaluation targets, duplicated training targets, raw baseline HKCanCor/
Tatoeba exposure and cross-split full-target substrings6+ are excluded before
decoding. Dictionary families preserve the original headword/duplicate/one-edit
grouping; the new sample extends the unchanged hash order beyond the previous800.
Targets retain NFC glyphs and exact reachable codes. Previous evaluations remain
regression/calibration material, not fresh independent evidence.

See [manifest](../tools/data/phrase_relations/manifest.json) and
[source/license notice](../tools/data/phrase_relations/NOTICE.md). Text is older
spoken dialogue/interview/parliament and dictionary usage, not measurements of
current private Hong Kong typing. Derived UD lexicon/weights retain CC BY-SA4.0.
words.hk NCDOL examples remain evaluation-only and are not APK assets.

## Bounded word relations

The optional PRR1 ranker tokenizes at most4-Han lexical units using the train-only
POS lexicon and small, project-authored function-word/category lists. It retains
up to12 trailing Han of editor context and six preceding tokens. Punctuation and
Latin reset relations. Longest lexical matches and conservative exact noun
categories avoid treating 錢包 as food, 花生 as a person, or 司機 as equipment.
Unknown nouns stay generic; unknown words remain reachable, not forbidden.

Features share subject/action surfaces, negation/action, classifier/noun category
and lexical head, action/object category/head, question/action, and typed role
sequences. Each feature contributes at most twice, weights are bounded to1.5,
and total relative evidence to2 before strength. This is a small statistical
relation scorer, not a complete dependency parser or proof of grammaticality.
No complete target string, gold completion or private context becomes a feature.

The actual current decoder supplies same-code competitors and existing adjusted
score offsets. Only gold targets already present in its confidence-eligible
pool96 generate ranking pairs. Up to three higher-scoring rivals within3 score
of a nonleading gold are mined; one close correct-head rival protects existing
success. Missing targets are reported, not injected. There are2,938 pairs from
782 independently grouped conversation, translation or authored-template families.
Minimum feature support is two real source families. Existing within-family
weights are normalized to real HK65%, Tatoeba20%, authored15%, a training priority
distinct from measured usage frequency. The model encodes about68KB.

## Selection and correction confidence

The [training protocol](../tools/data/phrase_relations/protocol.json) precedes
trial decoding. The first unrestricted correction improves natural top5
117→122 at strength1 but loses written first46→44 and public top5 131→130.
Its generic role density is not sufficient evidence to change an established
winner. These outputs become calibration, not new independent evidence.

The [policy amendment](../tools/data/phrase_relations/policy-protocol.json)
keeps weights/features fixed and compares with the actual legacy final winner.
Any lift needs two distinct positively trained lexical relation families and
new supported evidence absent in the winner. Subject feature variants count as
one family. An initial0.1 coefficient gate rejected most real learned signals
(median positive lexical coefficient0.01734); it is replaced by nonzero positive
weights already satisfying independent-family support. Actual score margins
remain separate confidence requirements.

The established first stays protected by default. An override requires lift≥0.5,
adjusted gap≥0.25, plus repaired adverse known-pattern evidence or additional
supported non-negation relations. Negation alone cannot make an opposite meaning
more coherent. Unknown O-role patterns do not count as adverse evidence. Explicit
known-word, character-sequence and context confirmations remain protected.
This changes ordering only, not raw confidence, beam48+8, the candidate pool96,
display20, dictionary, signing, application ID, layouts or personal-learning schema.

The803 calibration cases require no first/top5/top20 loss in each set. Selection
maximizes equally weighted set MRR, lower strength on ties; the selected strength
is0.5. The803 full native top20 lists match Python simulation exactly. All5,201
training/probe feature vectors, serialized scores and guarded lifts match Java
exactly. The selected scorer increases known public top20 coverage154→155.
Other calibration aggregate first/top5/top20 counts remain unchanged.

## Reproduction and verification

```sh
source /workspace/android-environment/activate.sh
python tools/prepare_phrase_relations.py /path/to/hkcancor-utf8.zip /path/to/pinned-UD-repo /path/to/wordshk.csv
# Re-observe the complete frozen train list, or merge complete cached old/new observations.
PYTHONPATH=tools python - <<'PY'
from pathlib import Path
from diagnose_sentence_priority import observe
observe(Path('tools/data/phrase_relations/train.tsv'), Path('/tmp/relation-observer.tsv'), revision='21ede20')
PY
python tools/train_phrase_relations.py train /tmp/relation-observer.tsv /tmp/relation-model
PYTHONPATH=tools python - <<'PY'
from pathlib import Path
from diagnose_sentence_priority import observe
observe(Path('tools/reports/phrase-relations-2026-10-14/calibration-cases.tsv'), Path('/tmp/validation-scored.tsv'), revision='21ede20')
PY
python tools/evaluate_phrase_relations.py /tmp/validation-scored.tsv /tmp/relation-model /tmp/calibration.json
python tools/verify_phrase_relation_parity.py /tmp/relation-model/pairs.tsv /tmp/relation-model/weights.json tools/data/phrase_relations/lexicon.json /tmp/parity.json
python tools/native_phrase_relations.py build /tmp/native-relations
# Copy the preserved trial into this temporary archive only; leave app assets untouched.
cp tools/data/phrase_relations/selected-relation-ranker.b64 /tmp/native-relations/app/src/main/assets/relation_ranker.b64
python tools/native_phrase_relations.py run /tmp/native-relations --cases tools/reports/phrase-relations-2026-10-14/calibration-cases.tsv --output /tmp/native.tsv
PYTHONPATH=tools python -m unittest tools/test_phrase_relations.py tools/test_source_balancing.py tools/test_daily_prefix.py tools/test_sentence_search.py tools/test_sentence_ranking.py
./gradlew testDebugUnitTest lintDebug --offline --max-workers=2
```

216 Java tests pass, including seven new relation/category/bounds tests;27 Python
tests pass, including source separation and unchanged old data/model reproduction.
Lint has no errors and25 existing warnings. On1,594 old regression targets,
aggregate first/top5/top20 are758/1119/1263 before and758/1120/1264 after;
no per-set metric decreases. Three simulated explicit Single confirmations
retain32/32 contextual first choices and489 sequence records, against30/32
legacy-only. Matching codes and output bounds are checked in native evaluation.
With the asset absent, all803 native candidate lists exactly match the frozen
baseline observer, verifying the production fallback separately from trial gains.

The pinned source extraction and complete model training reproduce all ten data
files, four unscaled model files and the selected encoded model byte-for-byte.
Only training observations can be merged or fit; the frozen manifest, feature
hash and old model hashes are checked by the trainer.

## Independent result and delivery decision

The selected strength0.5 and runtime hashes were saved in
[selection.json](../tools/data/phrase_relations/selection.json) before decoding
the796 reserve. No weight, feature, target or runtime-policy adjustment follows
these outcomes. Native baseline and trial use the same codes, sources and old
assets. The sample is now observed evaluation material, not a future blind test.

| Unused source | Cases | First before/after | Top5 before/after | Top20 before/after |
| --- | ---: | ---: | ---: | ---: |
| Dictionary example families |500 |94 /94 |178 /177 |250 /250 |
| Parliament utterances |296 |86 /86 |160 /160 |192 /192 |
| Combined |796 |180 /180 |338 /337 |442 /442 |

Four targets change rank:19→18,15→10,7→8 and5→6. The last loses a top5 hit;
none gains one. There are68 changed top20 lists, but moving other candidates is
not evidence of improved intended-target accuracy. The written sample's MRR
changes0.26410561→0.26407574; parliament's remains0.39633305. This fails the
predeclared independent no-loss/useful-gain rule, despite passing old regression
counts. Do not install this trial asset or claim a1.0 improvement.

The quiet desktop comparison uses one JVM, isolated class loaders, alternating
before/after order, CPU0,12 warm-up passes and15 timed samples per code. Across
five ordinary codes and one48-letter pressure code, the maximum wall median
ratio is1.014 and CPU median ratio1.018. Trial ordinary medians range83–232ms;
pressure is661ms. The ratio is below1.2, but host timings and apparent speedups
are not Fold7 latency measurements or a promised input-speed improvement.

The full [work report](../tools/reports/phrase-relations-work-2026-10-14.json)
links calibration, regression, parity, reproduction, paired timing and all796
paired candidate lists. Code0.6.39/versionCode46, signing and private-learning
files remain unchanged; no APK is produced. A later trial needs a new unobserved
source reserve and useful independent gains before enabling its model.
