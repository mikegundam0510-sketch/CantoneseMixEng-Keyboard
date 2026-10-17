# Sentence pretraining before same-code adaptation

This experiment implements the user's next direction after the rejected
[current-search fit](CURRENT_SEARCH_TRAINING.md): train a causal language model
on licensed Cantonese text, then adapt those same parameters to actual same-code
TRAIN rivals. Parent `1a6a67e` has the unchanged production app from `e209474`.
That production primary5gram already had corpus training; the new experiment
adds a recurrent language foundation and Common Voice prompts. It does not claim
to introduce corpus learning to the keyboard for the first time.

## Source audit and grouped data

The original clean text corpus and current-parent final rivals retain HKCanCor,
Tatoeba, UD and project-authored attributions. The new published source is
Common Voice's9,444 Cantonese Sentence Collector rows, pinned at revision
`46407be8d4c5de28b62baf2b18a363ea461b3c4f`, SHA256
`645d6a544634db879cef9d38e13ce58b7cef91772ba4d2ae6f6f674dbeb02a8b`.
The official CC0 contribution terms and public-domain admission documentation
are pinned in `tools/data/sentence_pretrain/source-audit.json`.

These are donated single read prompts, not additional Hong Kong conversations.
The source supplies no author IDs. Exact, one-edit and specific shared16-character
near duplicates share a cluster; all prompts are TRAIN only. We cannot claim
unseen-contributor validation on that source. We honour Mozilla's request against
dataset mirroring by keeping the raw and derived text cache in ignored `.native`;
Git contains only code, hashes, counts, provenance and trained weights.

SpiCE's official documentation establishes CC BY4.0 licensing, but its original
download destinations are outside the current network allowlist. No original
request was made and no SpiCE text is admitted. CantoMap's original data requires
researcher access on request and is also not admitted. We do not substitute
unattributed scraped film, forum or private-message data.

All non-Han characters split spans; boundaries including spaced English remain
boundaries. Normalization is NFC plus the six previously reviewed glyph pairs.
Only original TRAIN HK conversations, translation families and UD subsets enter.
Internal validation uses the same deterministic conversation/translation/scenario
family split in both stages. TRAIN spans containing an internal validation target
of six or more characters are excluded. External evaluation targets, including
reviewed-normalized forms and the untouched reserve500, are used solely to
exclude full target/span containment of at least six characters. This is not a
claim to detect every semantic paraphrase or all possible near duplicates.

| Domain | Pretrain TRAIN spans | Internal validation spans | Adaptation TRAIN rivals | Internal validation rivals |
|---|---:|---:|---:|---:|
| HKCanCor |16,302|2,484|11,864|1,842|
| Common Voice prompts |12,135|0|0|0|
| Tatoeba |4,313|462|5,457|669|
| UD |226|0|672|0|
| Authored/daily |702|78|2,011|217|
| Total |33,678|3,024|20,004|2,728|

There are252,442 TRAIN and22,048 internal-validation Han characters. Prompt rows
may produce several boundary-safe spans, hence12,135 spans from fewer raw rows.
Two source pairs overlap external evaluation and six more TRAIN pairs overlap
internal validation and are excluded. Six full prompt rows belong to externally
overlapping clusters and are rejected. The complete preparation replays
byte-identically for corpus, pairs and manifest.

## Model and two training stages

One reset-after GRU has32-dimensional character embeddings and32 hidden units.
Vocabulary uses only LM-TRAIN characters with at least three occurrences and two
supporting source families/clusters, capped at4,093 plus PAD/UNK/BOS. This support
is not an independent-speaker count. A Huffman hierarchical-softmax tree gives
a normalized next-character distribution while scoring only the target's path.

Pretraining minimizes mean next-character negative log probability, initialized
to the TRAIN unigram tree distribution. It runs20 fixed epochs with Adam rate
.003 and batch128. Adaptation starts from the best internal-LM checkpoint and
runs12 epochs at rate.0005 on the current-parent same-code comparisons. Its loss
is baseline-offset pair softplus plus.05 positive next-character loss. Baseline
raw/final-min offsets are clipped[-4,4]; they approximate the final path margin
and are not inferred from evaluation answers. Prefix comparisons are not used
by this experiment. All predictions remain ordinary answer-free inference.

Both stages use seed20261017, global gradient norm bound5, family/case/rival
normalized source mass and checkpoints chosen solely on their respective
internal objectives. No external keyboard accuracy selects an epoch. The fixed
LM source mix is HK65%, prompts20%, Tatoeba10%, UD2.5%, authored2.5%; adaptation
is HK70%, Tatoeba20%, UD5%, authored5%. Missing internal-validation domains are
renormalized rather than filled with prompt examples. There is no L2 term.

The deployed evidence is fixed for both arms:

`0.5 * 2 * tanh(mean(log P(char | causal GRU history) - log TRAIN unigram prior))`

It is added once to whole-candidate ordering alongside the existing sentence
ranker, before the existing personal and confidence gates. It reads at most12
contiguous prior Han characters and48 composing characters, and returns neutral
for invalid/overlong composing text. It keeps no editor text or personal record.
Final scoring cannot restore a path already pruned by the unchanged beam.

The three-way comparison is parent, language-only checkpoint and the adapted
checkpoint of the same architecture and strength. It does not independently
isolate the effects of added source data, architecture or source weighting.
There is no extra strength/architecture grid after observing their outcomes.

## Frozen gates and implementation checks

`protocol.json` and `seal.json` pin120 source/assets and six evaluation references
before the first fit or ordinary candidate result. The already observed1,450
cases are calibration. New150 and old1300 first/top5/top20 must all be preserved,
new150 must gain first/top5, and old per-set first/top5 loss must stay within1pp.
Select equal-set mean first/top5/top20/MRR; ties prefer language-only.

Only a selected model proceeds to the fixed3,893 guard, actual enabled Single32,
isolated Android unit/Lint, and quiet same-JVM paired timing (30 warmups,
11samples, six fixed codes, every wall/CPU ratio at most1.2). Guard aggregate
first/top5/top20 must be preserved and per-set first/top5 loss stay within1pp.
An exact source/model/evidence freeze is required before one parent/candidate
pass on the still-unused context-search500. Adoption there requires no first/
top5/top20 loss and a first/top5 net gain. No post-outcome fitting or threshold
changes. A substantial-gain claim requires at least25 extra top5 hits out of500;
the original separate1.0/device requirements still apply.

Seven reference tests pass, including26 finite-difference gradient coordinates
for both objectives, normalized hierarchical probabilities, neutral unigram
initialization, padding, Unicode/boundaries, deterministic binary roundtrip,
two-stage family separation, exact-code TRAIN membership and external-target
exclusion. A controlled Java decode changes `丙乙` to `甲乙` only with a deliberately
supporting model enabled. The fixture passes80 Java/Python score comparisons and
rejects15 malformed files. These are implementation checks, not typing hit rates.
Actual fitted models receive separate full-vocabulary verification.

## Reproduction

Use the existing Java17 activation and NumPy2.3.5 with one BLAS thread. Download
the official pinned Common Voice file to a local path, verify the SHA256 above,
and use fresh output folders. Do not commit the resulting text cache.

```sh
source /workspace/android-environment/activate.sh
python3 tools/prepare_sentence_pretrain.py /tmp/sentence-collector.txt \
  .native/sentence-pretrain-20261017/data
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONPATH=tools \
  python3 -m unittest test_sentence_pretrain
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/train_sentence_pretrain.py \
  .native/sentence-pretrain-20261017/data /tmp/sentence-models
python3 tools/run_sentence_pretrain.py prepare /tmp/sentence-native /tmp/sentence-models
python3 tools/verify_sentence_pretrain.py /tmp/sentence-native/language /tmp/language-check.txt
python3 tools/run_sentence_pretrain.py run /tmp/sentence-native language \
  tools/data/context_search/calibration1450.tsv /tmp/sentence-results/language.tsv
python3 tools/run_sentence_pretrain.py run /tmp/sentence-native adapted \
  tools/data/context_search/calibration1450.tsv /tmp/sentence-results/adapted.tsv
python3 tools/run_sentence_pretrain.py report /tmp/sentence-results
```

The committed manifest and seal must match rebuilt data and fitted sources.
Guard harnesses explicitly load the optional model; an old null constructor is
insufficient to verify enabled personal learning, performance or Android wiring.
Version0.6.39/code46, signing, local learning storage and Fold7 layout stay in
place while the experiment is evaluated. No APK is requested.

## Completed calibration and delivery decision

| Model | New150 first/top5/top20 | Old1300 first/top5/top20 | Combined1450 first/top5/top20 |
|---|---|---|---|
| Parent |22/53/77|279/505/659|301/558/736|
| Language only |28/56/75|289/514/666|317/570/741|
| Language plus same-code adaptation |26/58/74|293/510/671|319/568/745|

Language-only gains19 and loses3 first choices (net+16), gains16 and loses4 top5
hits (net+12). Adaptation gains25 and loses7 first choices (net+18), gains18 and
loses8 top5 hits (net+10). Relative to language-only, adaptation gains two first
choices overall but loses two top5 hits. Thus adaptation is a tradeoff here,
not a uniform improvement. Complete paired changes and ordinary candidate lists
are archived; any p-values emitted by the generic report are descriptive on
already observed calibration, not independent statistical confirmation.

Both arms improve aggregate first/top5/top20 and preserve the old-set gates, but
both **fail** the fixed new150 top20 rule. Language-only loses two previously
visible targets with no new coverage gains in that subset; adaptation loses
those two and a third:

- 「我鍾意住喺市中心交通方便去邊都易啲」: parent rank14, missing in both.
- 「佢屋企辦喜事啊」: parent rank15, missing in both.
- 「呢個機場每日二十個航班」: parent rank17, missing after adaptation.

Prefix search and vocabulary are unchanged by these arms. The observed losses
occur after adding the final candidate evidence, rather than a new beam policy.
The list-only analysis does not distinguish a display20 boundary from downstream
confidence/head filtering. We do not alter weights or filter thresholds to fit
these examples. A future separately frozen experiment can test preserving the
available parent candidates while reranking them; it is not an extra trial in
this closed model grid.

The observed gains are larger than the preceding current-search fit's+4 first/
+2 top5 on the same1,450 calibration, but still do not establish unseen typing
accuracy or1.0 readiness. Both new checkpoints are rejected for production.
The3,893 guard, enabled Single32, Android checks, quiet timing and independent500
are not run after calibration rejection. No speed or on-device-learning gain is
claimed. The unused context-search500 remains available for a future qualified
candidate. No packaging task is run.

Production Java/assets,0.6.39/code46, signing, personal-learning storage and Fold7
layout remain unchanged. The completed research is saved under
`tools/reports/sentence-pretrain-2026-10-17`, with the final decision in
`tools/data/sentence_pretrain/decision.json`.

## Fitted model and numerical evidence

The fitted vocabulary has2,251 entries including special tokens. Its recurrent
and hierarchical parameters are identical in shape across both arms. The actual
Java model uses650,315 primitive-array bytes. Each full fitted arm passes80
Java/Python score rows and15 malformed-model rejections; the optional-null
constructor preserves20 complete cached parent candidate lists exactly.

The best pretraining checkpoint is epoch9: internal next-character objective
5.7184949602 at unigram initialization becomes4.5016038683. Adaptation selects
epoch11, reducing its internal combined pair/positive-language objective from
0.4534118322 to0.4468004529. These two objectives differ and are not comparable
percentages or typing hit rates. Epoch choices use only the previously frozen
family-disjoint internal split. The full ordinary-model source/class/asset
hashes are recorded in `inference-freeze.json` before calibration results.

Both complete seeded training stages replay byte-identically for
`language.b64`, `adapted.b64` and the full fit report, independently of the first
fit. This verifies execution reproducibility, not accuracy on new users.
