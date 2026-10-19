# Retain the deployed pool before supplementing new characters (not adopted)

The independent500 comparison shows no hit-rate gain, so the frozen candidate
is not adopted. All169 existing tracked app files remain byte-identical to
`1b13d01`/`d7dec75`. Research tools, the exported model and outcomes are retained
for review. Version0.6.39/code46, signing, local learning and Fold7 layout remain
unchanged; no APK is produced and no1.0 improvement is claimed.

This fixed experiment addresses the preceding vocabulary replacement failure.
The old2248-character generator remains fully active. Its entire displayed pool
reaches the final comparison before the unchanged2493-character model can offer
strings containing at least one of its245 TRAIN-selected additions. No model is
refitted and no evaluation example selects characters or scoring thresholds.

The first `min(18, deployed-count)` choices stay exact, including choices from
the old generator on shorter native lists. At most two final slots use the same
existing whole-text score as production. All old final choices remain eligible,
ties favour them and surviving old choices keep their relative order. Total
display remains at most20. Keeping the complete old pool does not guarantee
that its last two choices always survive competition.

The expanded provider's ordinary beam24/top20 outputs are filtered after
generation, without searching farther to fill the filtered list. New offers
must contain a newly added character and match the actual dictionary's code.
The score remains language+sentence+aligned-relation correction referenced to
the original head; neural generation probability does not rank the final pool.
Personal confirmations/rejections and learned sequences bypass expansion.
Mixed input and translation prefixes keep their existing baseline path.

The parent is `1b13d01`, whose tracked app tree is identical to adopted
`d7dec75`. Compare with its complete deployed candidates, not the older
unsupplemented decoder. The original replacement/compatibility trials and all
their failed results remain immutable.

## Known comparisons

| Known set | First, before→after | Top5, before→after | Top20, before→after |
| --- | ---: | ---: | ---: |
| 1450 | 301→301 | 568→568 | 738→739 |
| 3893 | 1358→1358 | 2263→2263 | 2729→2730 |

Each comparison gains one top20 answer and loses none. Every named subset is
nondecreasing and each deployed first18 prefix is identical. The four answers
lost by the preceding expanded-provider replacement all survive here, at their
original ranks. These sets were already observed, overlap in places and are
not independent proof of general accuracy; their counts must not be pooled to
claim a fresh success rate. Gains occur at the tail, not in the first five.

There are16 changed displays on1450 (18 additions,16 removals) and148 on3893
(234 additions,26 removals). Most display changes do not recover the reference
answer. This is not a substantial hit-rate or1.0 result.

## Qualification and reproducibility

The protocol and inference hashes are sealed before fusion predictions. Cached
ordinary expanded outputs are reused only on identical known inputs. The prior
compatibility trial skipped269 short-list guard inputs; these receive ordinary
expanded inference here, without consulting labels or ranks. Prediction inputs
carry only context, code and candidate lists. Labels are joined after inference.

The Java loader accepts exactly the old2251-token and expanded2496-token schema
sizes before allocating arrays. All old numerical search operations remain
unchanged. Two immutable providers retain per-call history/search state. The
additional primitive weight arrays occupy836,808 bytes; this design does not
share a single weight copy. Cold startup and Fold7 latency require device work.

Mathematical checks compare85 ordered/score outputs for each provider (170
total), maximum score error below0.000004. Twenty malformed-model inputs are
rejected for each provider, including invalid sizes, nonfinite weights, truncated
or trailing data. Cancellation and invalid code limits are checked. Eleven
existing slot-policy checks and eight fusion checks protect previous generated
prefixes, old tail eligibility, Unicode supplementary characters, ties,
personal bypass and the ordinary20-proposal bound.

The complete actual Java pipeline reproduces all5,343 ordered screening lists.
Four active cold fixtures verify missing expansion, an expansion with no added
alphabet, missing legacy provider, confirmed/rejected context, familiar legacy
choices, mixed input and translated prefixes. The simulated Single32 test
learns489 sequence records after three confirmations: legacy first/top5/top20
30/32/32 and contextual32/32/32. Every learned display matches the actual
deployed baseline, including its old generator. Android222 unit tests pass
with zero failures/errors/skips; Lint reports25 warnings and zero errors.
The exact optional service loader/constructor and inference weights are tested.

Quiet paired timing alternates archived deployed/candidate classes in one JVM,
30 warmups and11 samples for each of six codes, including48 letters. Maximum
wall/thread-CPU ratio is1.060615, about6.1% slower. This passes the predeclared
1.2 bound but is not a Fold7, cold-start or broad device-performance result.

## Independent outcome and delivery

All preceding gates and implementation hashes are frozen before the new500
comparison. The parent runs from its unmodified archived classes, including
the old generator. The candidate then runs the same target-free inputs through
its complete pipeline. There is one pass per arm, no refit or policy change.

| Previously reserved500 | First | Top5 | Top20 | MRR |
| --- | ---: | ---: | ---: | ---: |
| Deployed parent | 90 | 206 | 261 | 0.282842 |
| Retained-pool candidate | 90 | 206 | 261 | 0.282842 |

No answer enters or leaves at any measured cutoff; each reference answer's rank
is unchanged. Every deployed first18 prefix is retained. The positive top20
gain gate fails, so the candidate remains research only. Passing technical
checks and repairing the preceding four losses do not establish general
accuracy gains. No further independent-based tuning occurs in this experiment.
All three recent500 sets are now observed; none can be called unseen again.
The preceding experiment's unused500 statement describes its historical stop,
before this separately qualified comparison consumed the same frozen reserve.

Full outcomes are in `tools/reports/retained-pool-2026-10-19/`; the decision and
pre-inference qualification are in `tools/data/retained_pool/`. The unchanged
app/model bytes are checked explicitly after rejecting adoption. The main
dictionary, personal-data formats and layout are untouched. The next accuracy
study should target existing sentence ranking rather than assume more tail
proposals will raise first/top5 success.

Code and source notices are in `tools/data/retained_pool/NOTICE.md`. Public
words.hk examples are NCDOL evaluation-only, never training or app assets. Raw
Common Voice views and all phone learning records are excluded from published
artifacts. Preserve all predecessor licences, models, protocols and results.

Historical commands use existing predecessor caches and protect completed
outputs. For reproduction, declare separate work/data/report paths instead of
overwriting the sealed trial:

```sh
source /workspace/android-environment/activate.sh
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python tools/retained_pool/study.py prepare
python tools/retained_pool/study.py inputs --name calibration1450
python tools/retained_pool/study.py run --name calibration1450
python tools/retained_pool/study.py report --name calibration1450
# If qualified, prepare each guard part0..3, then run/report guard3893.
python tools/retained_pool/study.py inputs --name guard3893 --part 0
python tools/retained_pool/study.py run --name guard3893
python tools/retained_pool/study.py report --name guard3893
python tools/retained_pool/port.py prepare
python tools/retained_pool/port.py parity
# Full ordinary Java decoding, parts0..3:
python tools/retained_pool/port.py run --part 0
python tools/retained_pool/guards.py report
python tools/retained_pool/guards.py prepare
python tools/retained_pool/guards.py learning
# Compile the separate parent driver against the unmodified archived parent:
javac -encoding UTF-8 \
  -sourcepath .native/retained-pool-20261019/native/app/src/main/java \
  -cp .native/retained-pool-20261019/native/classes \
  -d .native/retained-pool-20261019/native/classes \
  tools/retained_pool/DeployedEvaluation.java
# In the exact archived Android checkout, run (no assemble/package target):
./gradlew --offline --no-daemon --max-workers=2 testDebugUnitTest lintDebug
# Back in the repository, with all other decoding/build jobs complete:
java -Xmx2g -cp .native/retained-pool-20261019/performance-classes \
  PairedRankingPerformance \
  .native/retained-pool-20261019/native/classes \
  .native/retained-pool-20261019/native/app/src/main/assets \
  .native/retained-pool-20261019/candidate/classes \
  .native/retained-pool-20261019/candidate/app/src/main/assets 30 11 \
  > tools/reports/retained-pool-2026-10-19/timing.tsv
# Parse actual completed Android/quiet timing results:
python tools/retained_pool/guards.py android
python tools/retained_pool/guards.py timing
python tools/retained_pool/guards.py qualify
python tools/retained_pool/independent.py start
python tools/retained_pool/independent.py parent
python tools/retained_pool/independent.py candidate
python tools/retained_pool/independent.py report
python tools/retained_pool/adopt.py
```

No APK or version/signing/local-storage/layout change is authorized by this
experiment. The app remains0.6.39/code46 pending a separately requested release.
