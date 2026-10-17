# Causal language scores during prefix search

User-authorized steps 1 and 2 start from adopted parent `28dfb69`: use the
existing Cantonese GRU during search, then adapt it on actual prefix repair and
protection comparisons. The production source remains unchanged until the
predeclared ordinary-output and implementation gates pass. No APK is requested.

## Fixed implementation

The existing 48-path beam and word/character/prefix reserves run first. A
separate reserve may append at most four histories per prune. Candidates must
be within four raw-score units of the old 48th path, absent from the old
survivors, and among at most eight inspected outside histories. Their bounded
causal mean log-probability versus TRAIN unigram score must exceed the old
48th path's neural score by 0.25. Proposals are ordered by raw score plus the
neural gap; existing histories stay distinct. No raw score is modified.

One session per decode reuses recurrent hidden states for common prefixes.
It has 128 score queries and at most 2,048 stored prefix states. Exhaustion
falls back to the old survivors; no text/state survives the decode. The same
immutable model can be shared by concurrent decodes with separate sessions.
Mixed input and translated prefixes use the existing baseline entry point,
which disables the search model. The established final tail reranker,
dictionary, confidence margin and final display size remain unchanged.

This preserves the original survivors at each individual prune, not entire
end-to-end candidate lists: downstream competition may displace a previously
visible candidate. Final accuracy, regression, learning and latency gates are
therefore necessary. This experiment does not inherit the preceding
experiment's strict original-first/list guarantee.

## Training and evaluation separation

The deterministic source-balanced subset contains 2,534 existing TRAIN
identities whose positive text was admitted by the original sentence-pretrain
cache. Original conversation/translation/scenario family splits are shared
with the checkpoint, so its original internal validation remains unfitted.
There are 2,048 fit identities and 486 internal validation identities; the
retained UD subset has no internally held-out family in this sample.

All selected identities are decoded again by the actual parent with the
deployed tail model enabled. The observer records actual first lost and
survived prefixes, their consumed codes, raw ranks and competitors. It runs
after the original prune and never inserts a gold path into inference. Five
TRAIN examples match the ordinary parent and null-model decoder exactly;
changing the observer's gold labels changes no emitted candidates.

After overlap exclusion, there are 6,514 comparisons: 5,293 fit and 1,221
internal validation, across 460 and 107 original families. Only 129 comparisons
have a lost positive (117 fit, 12 validation); most protect a surviving prefix.
No lost HKCanCor positive remains in this fit subset. Thus this is a small
repair signal and is not evidence of broad coverage of Hong Kong typing errors.
No reconstructed or forced gold prefix is used.

The fit starts from the adopted checkpoint, with fixed vocabulary/unigram and
32-dimensional architecture. Eight seeded Adam epochs, rate 0.0002, batch 128,
family/case/rival-balanced source weights and 0.05 positive LM auxiliary are
fixed before fitting. Offset is zero because survival compares the neural gap;
the raw score is used separately for the floor/proposal order. Checkpoint
selection uses only original-family-disjoint internal loss. Internal loss
0.637795→0.588279 (epoch 8) is not a keyboard hit-rate result.

Before any fit or ordinary trial, source capacity was audited. Excluding all
tracked targets, previously used dictionary families and the complete
pretrain/adaptation text (including Common Voice) leaves only 543 unused public
dictionary groups. The experiment reserves 500 of them and uses the existing
1,450 examples for calibration. An initial 200+500 capacity request failed
before fitting/decoding and was reduced for source capacity, without outcome
filters. The new reserve must stay unused unless every earlier gate passes.
The preceding context-search500 is not decoded or selected on again.

## Protocol and checks

`tools/data/prefix_language/protocol.json` and its seal precede fitting and
ordinary candidate outcomes. Two arms only: `language` reuses the adopted
checkpoint in the prefix reserve; `trained` uses the selected prefix-adapted
checkpoint. Each native source/class/asset set is additionally frozen before
its ordinary run. No post-outcome policy, strength or architecture grid.

Known 1,450-case calibration compares against the adopted parent's cached
output. First/top5/top20 must not decrease separately on the 150 and 1,300
groups, aggregate top20 must improve, and each set's first/top5 loss must stay
within one percentage point. Select equal-set mean top20, first, top5 and MRR,
with ties favoring `language`. Selected candidates then need the known 3,893
guard, enabled Single32, enabled numerical/implementation checks, exact wired
Android tests/Lint and quiet paired 30-warmup/11-sample wall/CPU medians at most
1.2 times the parent. Only then may the new reserve500 run once per arm, with
nondecreasing first/top5/top20 and a top20 gain required for adoption.

Both checkpoints pass 340 prefix-score comparisons against the full scorer.
A controlled live prune retains all original 48 paths and rescues a 49th;
neutral weights and the disabled entry point preserve the original output.
Session lifetime, query limits and bounded state storage are checked.

## Result: research only

Both complete ordinary runs compare against the adopted parent's exact cached
1,450 cases. Frozen source/model/class/asset hashes and ordered shard identities
are checked before merging. Results are:

| Scheme | First | Top5 | Top20 |
| --- | ---: | ---: | ---: |
| Adopted parent | 301 | 568 | 736 |
| Prefix reserve, unchanged language weights | 301 | 568 | 736 |
| Prefix reserve, prefix-adapted weights | 301 | 568 | 736 |

Each arm changes 15 candidate sets, so the reserve does reach ordinary outputs,
but neither adds a correct target. The unchanged-weight arm's MRR changes
0.2894391→0.2894347; the trained arm's MRR is unchanged. All fixed count and
per-set regression gates pass, but the required top20 coverage gain fails for
both. No arm is selected, and the production app stays at the adopted parent.

After this rejection, the trained arm receives a research-only quiet paired
timing check. Both the parent's deployed language model and the candidate's
additional search model are actually loaded. Thirty warmups and eleven
alternating-order samples over six fixed codes pass the 1.2 ceiling; maximum
wall/thread-CPU median ratio is 1.061681. For the 48-letter stress case, wall
median is 524.175→526.675ms. This does not compensate for zero extra hit counts
and is not physical Fold7 latency. Timing the unchanged-weight control is not
needed for this rejected experiment.

The trained weights pass 80 Java/Python score cases and reject 15 malformed
model variants; immutable primitive model arrays use 650,315 bytes. A separate
stress fixture forces the session to reach exactly 2,048 states and verifies
that exhaustion returns unavailable evidence without subsequent cache growth.
This stress test runs after the quiet timing check, without changing runtime
code or weights. Initial fixture-only issues (minimum dictionary size and an
input/output path collision in the first parity attempt) were corrected before
the successful implementation checks; neither affects ordinary inference.

Because calibration fails, the 3,893-case guard, Single32 and wired Android
unit/Lint gates are **not run** for this candidate. No new APK or UI/persistence
claim is made. The new 500-case reserve remains undecoded; the previous
context-search500 is not decoded again. Version 0.6.39/code 46, signing,
personalization storage and all app source/assets remain byte-identical to
`28dfb69`. Protocol, models and results remain for review, not deployment.

Records are in
[`tools/reports/prefix-language-2026-10-17/`](../tools/reports/prefix-language-2026-10-17/),
with the final decision in
[`tools/data/prefix_language/decision.json`](../tools/data/prefix_language/decision.json).
The limited actual-loss subset is a training limitation, not a demonstrated
explanation of every missed sentence. Larger improvement requires evidence
covering the actual missing-path or final-selection failures.

## Reproduction

Use the existing Java 17 activation and NumPy environment. Public source text
retains the source and attribution requirements in the data notice. Native
archives and Common Voice-containing predecessor caches remain ignored.

```sh
source /workspace/android-environment/activate.sh
python3 tools/prefix_language/prepare_data.py
python3 tools/prefix_language/experiment.py observer /tmp/prefix-observer
# Run the four fixed observation partitions with the observer driver.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/prefix_language/train.py
python3 tools/prefix_language/experiment.py candidate /tmp/prefix-trained \
  --checkpoint tools/data/prefix_language/model/prefix.b64
```

These are historical commands for the original run. Preparation refuses an
existing input manifest, and fitting refuses an existing model directory.
Fitting collects observations before that model-directory check, so do not
invoke it in place on this completed archive. Reproduction requires separate
output paths and an auditable new seal; it must not replace this experiment's
data or reuse its reserve for future selection.
