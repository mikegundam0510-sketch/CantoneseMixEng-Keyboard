# Conservative tail supplementation

Adopted after all declared gates pass, including the independent500. The
independent coverage gain is only one target, with no losses: 254→255/500.
This is a small result, not evidence of a large general improvement or a
1.0 milestone. The app remains 0.6.39/code46; no APK is produced.

This study follows the rejected direct-code fusion experiment. It uses the
same frozen teacher generator only to propose complete strings. Existing
native models decide whether a proposal deserves one of two final slots.
No training, vocabulary expansion, personal data collection or new ranking
weights are involved. Parent `aedb58c` has the adopted `28dfb69` app tree.

## Fixed rule

Keep the original first 18 candidates at exactly the same positions. Compare
the original final two with at most 20 unique, dictionary-legal generated
strings. Use `QuickDecoder.languageScore + SentenceRanker.score` and the
existing aligned relation correction relative to the original first choice.
This is a common whole-text native scoring surface; it does not reproduce
the lattice's token priors. The generator's conditional probabilities are
not used to reorder native choices.

Select at most two final slots. Ties favour the original candidates. Surviving
native candidates retain their relative order; new strings follow them.
Shorter native lists can append at most two, with a total limit of 20.
Lists with fewer than five candidates bypass supplementation. Nonfinite
scores, unavailable proposals and cancellation retain the original list.
The ordinary Chinese decoder protects learned whole words, confirmed or
rejected contextual sequences and fully learned character sequences.
Mixed Chinese/English and translated prefixes retain their existing bypass.

The teacher source was chosen using previously observed calibration evidence:
it had recovered 20 targets missing from the native display, versus 17 for
the adapted checkpoint. This choice is informed by known results. Neither
the 1,450-case calibration nor the 3,893-case regression comparison is an
independent accuracy estimate. No threshold or slot-count grid is tried.

## Screening

| Known cases | Original first / top5 / top20 | Supplement first / top5 / top20 |
| --- | --- | --- |
| 1,450 | 301 / 568 / 736 | 301 / 568 / 738 |
| 3,893 | 1,358 / 2,263 / 2,625 | 1,358 / 2,263 / 2,729 |

The first comparison gains three targets and loses one; the larger comparison
gains 105 and loses one. These are separate existing sets, not a pooled fresh
sample. Every named set has nondecreasing counts. The screening runs the
actual original Java scorers on target-free inputs with frozen Python-generated
proposals. Labels and stored ranks are stripped before prediction, then joined
only to calculate the results. A 40-candidate union is never counted as the
20-candidate display.

## Native implementation and verification

The Java generator is a direct implementation of the frozen teacher's
32-dimensional character GRU and 16-dimensional remaining-code encoder.
It uses the same 2,248 characters, 2,479 legal code choices, all legal edges,
24 histories per consumed-code position, complete consumption and final 20
strings. Its primitive weights occupy 757,428 bytes. The exported binary
has a versioned, bounded header, sorted Han vocabulary and legal code facts;
loading rejects nonfinite weights, truncation and trailing data. Model state
is immutable, and editor history/search state stays within each call.

Eighty TRAIN inputs plus five boundary/context inputs produce the same ordered
candidates as Python, with maximum absolute sequence-score error below 4e-6.
Fifteen corrupt exports are rejected. Additional checks exercise cancellation,
invalid input, native displacement limits, duplicate and illegal proposals,
personal confirmations/rejections, missing-model fallback, mixed input and
translated prefixes. The ordinary complete Java decoder is evaluated separately
on all 5,343 known cases. Every list exactly matches the screening result;
all first18, legality, displacement and display-limit checks pass.

The enabled Single learning simulation preserves both complete learned displays
relative to the parent: legacy 30/32 first, contextual 32/32 first after three
confirmations, with 489 sequence records. No persistence format changes.
The exact optional loader and model are wired into an isolated Android archive:
222 unit tests pass without failures/errors/skips; Lint reports no errors and
25 existing warnings. These checks do not package an APK. The initial Gradle
attempt could not open local lock communication inside the sandbox; retrying
with normal local networking completes successfully.

## Independent result and adoption

All inference sources, models, compiled classes, native/Android wiring and evidence were
frozen in `qualification.json` before either independent decoder ran. The
unmodified parent classes and the complete candidate each decoded every
`prefix_language/reserve.tsv` case once. Gold-free inputs were used for both;
labels were joined after the predictions were complete. Markers prevent reuse.

| Independent500 | First | Top5 | Top20 |
| --- | ---: | ---: | ---: |
| Parent | 97 | 200 | 254 |
| Conservative supplement | 97 | 200 | 255 |

One target enters the display, none leaves; every original first18 stays
identical. Coverage changes 50.8%→51.0%, an absolute 0.2 percentage points.
The paired two-sided exact p-value is1: the evidence is too small for a broad
accuracy claim. First-choice and top5 accuracy do not improve in this step.
The much larger gain on previously observed3893 should not be substituted
for this independent result. Both the earlier context_search500 and this
prefix_language500 have now been consumed and cannot be called unseen again.

Quiet timing uses the exact loaded model in both complete decoders: 30 warmups
and11 alternating samples per code. The maximum wall/CPU ratio is1.021223,
about2.1% higher; some small negative differences are measurement variation,
not evidence of a speed improvement. Loading/startup and physical Fold7 latency
are not established by this benchmark.

Only the exact tested Java decoder, immutable generator, tail policy, optional
service loader and model are copied into the app. SHA checks in `adoption.json`
prove byte equality with the wired Android archive. The other163 original app
files remain unchanged, including version, layout and learning implementation.
Stable signing configuration and the application identifier are retained.
No APK is built. The derived weights and retained dictionary code facts have
bundled attribution under `licenses/code-generator/`; predecessor experiments
and checkpoints remain unchanged.

## Gates and reproduction

The sealed protocol requires exact original first18 retention, no first/top5
count changes, positive aggregate top20 gain on known1,450 and nondecreasing
top20 separately on its new150 and old1,300 groups and each named set. The
3,893-case guard requires nondecreasing first/top5/top20 in aggregate and every
named set. The larger screening runs before the Java port to avoid spending
effort on a policy that already regresses.

Full Java lists, Single32, the exact wired Android candidate's unit tests/Lint
and a quiet paired same-JVM timing gate must pass before the unused
`prefix_language/reserve.tsv` 500 can be decoded. Timing uses 30 warmups,
11 alternating samples on six codes, with every wall and thread-CPU ratio at
most 1.2. It is cloud-host timing, not physical Fold7 latency.

An eligible exact candidate, source/model bytes and evidence must be sealed
before one parent/candidate independent500 pass. That pass requires original
first18 retention, no first/top5/top20 count loss and positive top20 gain.
There is no tuning after this outcome. The earlier `context_search` 500 is
already observed and is not decoded again. No APK, version/signing, storage
or Fold7 changes are authorized in this study.

Source is under `tools/tail_supplement/`; protocol, exports and freezes are
under `tools/data/tail_supplement/`; outputs are under
`tools/reports/tail-supplement-2026-10-18/`. The previous failed experiments
and checkpoints remain immutable. Source notices are linked from the new
data directory's `NOTICE.md`. Full Common Voice prompt caches remain ignored.

Historical stage commands (completed outputs refuse replacement):

```sh
source /workspace/android-environment/activate.sh
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python tools/tail_supplement/study.py prepare
python tools/tail_supplement/study.py run
python tools/tail_supplement/study.py report
python tools/tail_supplement/guard.py prepare
# Generate fixed strided parts0..3, then evaluate the known regression guard.
python tools/tail_supplement/guard.py generate --part 0
python tools/tail_supplement/guard.py evaluate
python tools/tail_supplement/port.py prepare
python tools/tail_supplement/check_port.py prepare
# Full Java runs use parts0..3, then full_report.py.
python tools/tail_supplement/check_port.py run --part 0
python tools/tail_supplement/full_report.py
```

Reproduction needs the pinned predecessor inputs and separate paths. Never
overwrite this study's outputs or reuse a consumed reserve as unseen data.
