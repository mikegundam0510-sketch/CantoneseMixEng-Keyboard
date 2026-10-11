# Cantonese community-sentence experiment

**Outcome: useful gains, but not adopted.** The selected model fails the
predeclared completion-question guard. All bundled app models remain unchanged;
source version stays 0.6.39 and no APK or 1.0 release was created. The attributed
corpus, reproducible importer/trainer and results are retained for further work.

This experiment supplements existing HKCanCor training with attributed Tatoeba
examples. It does not collect private chats or establish current Hong Kong usage
frequencies. The public distribution snapshot is dated 2023-04-08; individual
sentence dates and authors are unavailable. See the [data notice](../tools/data/tatoeba_corpus/NOTICE.md).

## Source and boundaries

The pinned Jyut Dictionary database contains 68,250 rows labelled `yue`, but only
**6,149** are linked to the Tatoeba Cantonese source. The importer requires that
source link as well as the language label. Other dictionaries' examples cannot
be imported under the Tatoeba license. No Windows executable is run.

After NFC/whitespace normalization, a conservative colloquial-marker and length
filter, duplicate removal and overlap exclusions, there are **4,655** records:
3,703 training (3,529 families), 451 validation (433 families), and 501 heldout
(467 families). Training preserves English and punctuation; model context stops
at those boundaries. It neither silently deletes English nor joins unrelated
Chinese fragments. Spelling and grammar are not automatically corrected.

Families are connected components of shared translation links, identical Han
chunks, and one-deletion signatures (which also group some substitutions).
Grouping precedes filtering and splitting. A deterministic hash assigns families
80/10/10; the realized counts need not have those exact proportions. Identical
chunks of at least six Han characters cannot cross splits. Some paraphrases can
remain undetected, and this is not an author-independent study.

Old HKCanCor utterances and prior regression targets of at least six Han
characters are excluded by substring overlap in either direction. The source
files and their hashes are in the manifest. Evaluation freezes at most 200
reachable, complete Han chunks of 6–16 characters per split, with at most one
chunk per family and no invented preceding context. Short dictionary words can
naturally be shared with previous models. A chunk is not necessarily a full
grammatical or mixed-language sentence.

## Model comparison

`protocol.json` fixes family weights 2/6/12 before decoder evaluation. Each
training family contributes a gram once, so repeated variants do not multiply
the apparent usage frequency. The existing character 1–5-gram interpolation is
retrained; phrase vocabulary and all other scorers are frozen. Runtime code and
personal-learning storage are unchanged.

An important reproducibility constraint: the current dictionary assets differ
from those used to train the bundled character model. Training with today's
assets would introduce an unrelated change. The experiment instead archives the
original three training assets from `5885daec1c43d676a525c543c8ab092532cb3150`.
The runner first requires byte-for-byte reproduction of the current bundled
`language_model.b64`, then trains the extra-corpus variants from those same inputs.
All decoder comparisons use the current vocabulary and remaining scorers.

Selection requires no aggregate top-1/top-5 regression on any of three
validation sets, then maximizes their mean reciprocal rank. The selected weight
is saved before running heldout/guard decoding. Acceptance additionally protects
old600, daily32, completion16, natural200 and the new Tatoeba heldout200. Authored
heldout120 is reported separately. The runner never copies a model into the app.
These safeguards protect aggregate counts, not every individual candidate.

## Reproduce

Use Python 3.11+ (stdlib only) and JDK 17. In this cloud environment activate
`/workspace/android-environment/activate.sh` before Java commands. Download the
portable ZIP linked by the notice, verify SHA256 against `manifest.json`, and
extract only `Jyut Dictionary/dict.db`. The database itself is checksum-pinned
by the importer. The large archive/database is not committed or bundled.

```sh
python3 tools/prepare_tatoeba_corpus.py /path/to/dict.db \
  /path/to/hkcancor-utf8.zip /tmp/tatoeba-corpus
python3 -m unittest discover -s tools -p 'test_tatoeba_corpus.py'

mkdir -p /tmp/original-lm-inputs
git archive 5885daec1c43d676a525c543c8ab092532cb3150 \
  app/src/main/assets/cangjie5.base.dict.yaml \
  app/src/main/assets/quick_phrases.tsv \
  app/src/main/assets/hk_phrases.tsv | tar -x -C /tmp/original-lm-inputs

python3 tools/evaluate_tatoeba_experiment.py /path/to/hkcancor-utf8.zip \
  /path/to/jyut6ping3.words.dict.yaml \
  /tmp/original-lm-inputs/app/src/main/assets /tmp/tatoeba-experiment
```

The evaluation runner uses the committed frozen corpus under
`tools/data/tatoeba_corpus/`; regenerate elsewhere and compare hashes first.
Existing HKCanCor and Rime input hashes are still enforced by the trainer.
Experimental assets, raw ranked outputs, model reports and selection decisions
are written only to the specified experiment directory.

## Results (2026-10-11)

Validation selected weight 2. Weights 6 and 12 improve the new examples further,
but reduce top-five matches on the existing natural validation set, so they are
ineligible. The setting was selected before the following guard results:

| Set | Cases | Previous top-1 / top-5 / top-20 | Experimental weight 2 |
| --- | ---: | --- | --- |
| New Tatoeba heldout | 200 | 64 / 105 / 124 | 81 / 131 / 157 |
| Existing natural utterances | 200 | 72 / 112 / 133 | 72 / 114 / 137 |
| Authored chat | 120 | 56 / 81 / 96 | 73 / 83 / 98 |
| Old examples | 600 | 282 / 423 / 477 | 286 / 427 / 484 |
| Daily examples | 32 | 20 / 29 / 32 | 21 / 30 / 32 |
| Completion questions | 16 | 16 / 16 / 16 | **14 / 16 / 16** |

`你交咗錢未` and `你交咗表未` move from first to second, behind `係交咗錢未`
and `係交咗表未`. Both intended sentences remain reachable, but that does not
meet the frozen requirement to preserve first choices. The guard is not relaxed
after observing these results, and heldout results are not used to try another
weight. Further work must address the pronoun/clause-start ambiguity and use a
new prospective evaluation; the observed sets are now regression evidence.

The 17 authored first-choice gains are second-to-first movements from only four
correlated template families (receiving a parcel, waiting for a bus, taking the
MTR, buying bread/milk). They are not 17 independent real-chat improvements.
The natural-heldout top-1 gain is zero, and the authored top-5 gain is only 1.67
percentage points; neither meets the existing 1.0 gate of five points.

Eight new Python tests cover source/license isolation, punctuation/Latin resets,
family transitivity/order independence, overlap exclusion, split tampering and
per-family count caps; the 24 existing corpus/ranker tests also pass. All seven
corpus output files and the selected model/report reproduce byte-for-byte.
Every displayed evaluation candidate is checked against its complete Quick code.
Simulated Single learning still produces 32/32 first choices after three explicit
confirmations (legacy learning alone: 30/32). No Android code/assets changed, so
Android checks and device/performance tests were not rerun for this rejected
model. Full selection, guards, hashes and limitations are in the
[work report](../tools/reports/tatoeba-corpus-work-2026-10-11.json).

## Other researched sources

The previously supplied words.hk word/count exports do not authorize using its
full example-sentence corpus, which carries a different noncommercial license.
KddRES has research/noncommercial restrictions, and CantoMap's transcripts are
available on request rather than in its public repository. None was imported.
SpiCE documents CC BY 4.0 interviews recorded in 2018–2020, but it represents
Cantonese-English speakers in Vancouver, not exclusively Hong Kong; its official
download remains unavailable through this environment's current network policy.
No interview data or audio was downloaded. Tatoeba was obtained from the public
GitHub redistribution identified above, without bypassing a blocked destination.
