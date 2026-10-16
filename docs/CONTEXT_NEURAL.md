# Longer-context recurrent whole-candidate experiment

After all four [bounded search policies](CONTEXT_SEARCH.md) fail their new150
gate, this separate experiment tests additional model capacity on the unchanged
`e209474` decoder. The rejected search grid remains closed. No Android source or
asset is replaced before qualification; version remains0.6.39/code46 with no APK.

## Model and supervised data

One reset-after GRU uses16-dimensional character embeddings and16 hidden units.
It reads up to12 contiguous preceding Han characters, a boundary token, and up
to48 composing characters. A bounded scalar output supplies whole-candidate
evidence alongside the existing SentenceRanker before the existing relation,
head and personal ranking gates. It is not added to individual token scores.
No full-sentence lookup table or source/family ID is an inference feature.

The embedding vocabulary has1,418 entries, including padding/unknown/boundary,
derived only from positive internal-TRAIN comparisons (minimum occurrence3 and
two supporting families). Unknown characters share an embedding; this does not
remove them from the keyboard dictionary. The trained primitive arrays use
102,816 bytes. The model keeps no editor text or mutable personal history.

There are19,827 final positive/real-rival comparisons from the frozen clean
licensed TRAIN data:11,131 HK,5,927 Tatoeba,667 UD and2,102 authored/daily pairs.
They have exact matching codes. Historical baseline offsets are clipped[-4,4];
they approximate the current parent margin and are not regenerated from a test.
This approximation and the source age remain limitations.

Family hashes split17,791 comparisons for fitting and2,036 for internal neural
validation. A case's rival comparisons share its mass, then families/domains
receive fixed65/20/5/10 HK/Tatoeba/UD/authored proportions. Internal validation
families never fit the recurrent parameters or embedding vocabulary. This is
still a TRAIN-derived calibration split, not independent keyboard evaluation.
Attribution is in [NOTICE.md](../tools/data/context_neural/NOTICE.md).

The frozen fit uses seed20261016,40epochs, Adam rate.003, batch128, L2=.0001,
global gradient norm limit5 and output cap2. Select only the minimum internal
validation pair-loss checkpoint. Exactly two residual strengths,.5 and1, are
predeclared; no additional architecture/strength grid follows their outcomes.

## Training and implementation verification

The selected checkpoint is epoch1: internal validation objective falls from
.247641 to.218342. Later epochs overfit this split; these numbers are not typing
accuracy or evidence of a real-world percentage gain. Both model assets and the
complete40epoch report reproduce byte-identically in an independent seeded run.

Six Python checks cover11 finite-difference gradient coordinates, padding,
sequence order beyond a shared final four characters, supplementary Unicode,
binary roundtrip, licensed TRAIN membership, internal family disjointness and
evaluation-target exclusion. Each residual passes60 Java/Python score comparisons
and rejects eight malformed model files. The loader bounds dimensions, vocabulary,
weights, model length and finite values. The scorer rejects empty/non-Han or
overlong composing strings and resets preceding context at non-Han boundaries.

The optional-null constructor reproduces20 complete ordinary baseline lists.
A controlled actual decode changes its first choice only when a deliberately
supporting recurrent fixture is loaded, proving the new scorer is connected.
These are implementation checks, not corpus hit rates. The real ablations use
the full model-enabled Java constructor and all parent assets.

## Frozen keyboard evaluation

The already observed150 plus old1300 are calibration, using exactly the previous
complete cases/baseline lists. Require nondecreasing new150 and old1300 first,
top5 and top20 counts, a new150 first/top5 gain and old per-set first/top5 losses
within one percentage point. Select equal-set mean first,top5,top20,MRR, then
the smaller strength. No source, model or code adjustment uses fresh500 outcomes.

Only a selected arm proceeds to the3,893 guard, **model-enabled** Single32,
Android/Lint and paired timing. Old harness constructors without the optional
model are insufficient for those checks. Freeze all source/model/evidence hashes
before one parent/candidate pass on the still-unobserved500 context-search
reserve. Adopt only with preserved first/top5/top20 and first/top5 net gain.
The original1.0 major/device gates remain separate.

## Result and delivery decision

| Residual | New150 first/top5/top20 | Old1300 first/top5/top20 | Qualified |
| --- | --- | --- | --- |
| Parent baseline |22/53/77|279/505/659| Reference |
| half, strength0.5 |25/57/74|274/502/662| New top20 and old first/top5 losses |
| full, strength1 |23/58/73|266/488/662| New top20 and old first/top5 losses |

Both strengths are rejected. The half arm improves new150 first/top5 by3/4,
but loses three new top20 hits and five/three old first/top5 hits. Across all
1,450 calibration cases it gains15 and loses17 first choices, gains14 and
loses13 top5 hits, and exchanges15 top20 hits for15 others. Aggregate top5
changes558 to559; that small net change does not meet the frozen preservation
gate. The full arm has larger old-set losses. Neither qualifies for adoption.

The complete ordinary lists and per-set paired changes are archived under
[`tools/reports/context-neural-2026-10-16`](../tools/reports/context-neural-2026-10-16).
The [work report](../tools/reports/context-neural-work-2026-10-16.json) records
implementation checks, reproducibility and the explicit rejection. The extra
3,893 guard, model-enabled Single32, Android/Lint, paired performance and fresh500
decoding are not run for rejected arms. No speed or phone-learning improvement
is inferred from the implementation checks. The500 reserve remains unused by
any decoder in either experiment.

No production Java class, Android asset, version, signing configuration,
personal-learning store or Fold7 layout changes. Research models remain under
`tools/`; no APK is produced. Production stays at the `e209474` implementation,
version0.6.39/code46. This work establishes no accuracy gain toward1.0.

The diagnosis still motivates testing prefix scoring on separate licensed TRAIN
data: final-only scoring cannot restore paths already pruned by the beam. A
future experiment should generate current-parent real-rival comparisons on
TRAIN and train prefix and complete-sentence decisions together, instead of
reusing historical final margins. That is a new hypothesis, not a demonstrated
improvement or another tuning pass on this frozen grid. These150 cases are now
observed calibration; reserve500 stays sealed until a new candidate passes all
predeclared safeguards.

## Reproduction

Use NumPy2.3.5 from `tools/context-neural-requirements.txt`; activate the existing
Java17 environment before Java steps. All output folders must be fresh.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=tools python3 -m unittest test_context_gru
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/train_context_gru.py fit \
  tools/data/context_neural /tmp/context-gru-models
python3 tools/run_context_gru.py prepare /tmp/context-gru-native /tmp/context-gru-models
OPENBLAS_NUM_THREADS=1 python3 tools/verify_context_gru.py /tmp/context-gru-native/half /tmp/half-score.txt
python3 tools/run_context_gru.py run /tmp/context-gru-native half \
  tools/data/context_search/calibration1450.tsv /tmp/gru-results/half.tsv
python3 tools/run_context_gru.py run /tmp/context-gru-native full \
  tools/data/context_search/calibration1450.tsv /tmp/gru-results/full.tsv
python3 tools/run_context_gru.py report /tmp/gru-results
```

`train_context_gru.py prepare --output /tmp/neural-data-replay` reconstructs the
pair archive/manifest from the pinned existing clean final comparisons.
The research b64 assets are not Android app assets until the frozen gates pass.
