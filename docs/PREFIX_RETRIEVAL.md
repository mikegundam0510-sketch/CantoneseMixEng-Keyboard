# Prefix retrieval experiments and survival diagnosis

The baseline is `d8575595b689916d8649e71e1a365224392683a9`, version0.6.39/code46.
This work tests whether omitted positive prefix features explain missing
sentences. Neither proposed runtime change qualifies for adoption. Production
Java, bundled models, learning schemas and signing configuration remain exactly
the baseline; no APK is built.

## Frozen evaluation and decision

Before trial decoding, the [protocol](../tools/data/prefix_retrieval/protocol.json)
and another100 validation/500 reserve examples were frozen. Sampling excludes
all earlier dictionary families, tracked6+ target substrings and pinned raw
HKCanCor/UD/Tatoeba training exposure. The original preparation defaults still
reproduce the previous search-recovery split byte for byte. New dictionary
examples remain NCDOL1.0 evaluation-only material; full attribution/license are
linked in [NOTICE](../tools/data/prefix_retrieval/NOTICE.md). They never train a
model or enter APK assets. No private phone data are collected.

The previously observed600 search-recovery cases plus the new100 validation
cases form700 calibration rows. These are selection/diagnosis data, not unseen
typing accuracy. A trial needs a useful top5/top20 gain on the old600 with no
per-set first/top5/top20 count loss before broader guards, Single and latency
checks. Since both fail this initial gate, further runtime qualification and
the new500 reserve decoding are unnecessary. The reserve outcomes stay unopened.

## Tested proposals

The existing inexpensive proposal retrieves positive two/three-character
endpoint words, one-character endings and one-by-one boundary evidence from
the first two matching hints. Full signed scoring already supports more
features, but cannot inspect a prefix that proposal retrieval omits.

The broad trial includes four-character suffix words, two/three-character
endings, all two-by-two boundaries against at most six exact matching hints,
and endpoint role categories. Calibration exposes that broad role evidence
also admits prefixes without lexical evidence. The second trial, declared
before its decode and before any reserve outcome, uses only lexical evidence:
words anywhere within trailing four Han characters, endings and hint boundaries.
Feature counts retain the model's cap2. Both keep the original48 paths,
existing reserves, raw floor,32 full scores and at most4 learned additions;
no weights or score thresholds are changed.

|700 calibration rows|First|Top five|Top twenty|
|---|---:|---:|---:|
|Baseline|152|280|362|
|Broad proposal|151|279|362|
|Lexical proposal|152|280|362|

The broad trial loses one correct first and top-five result. The lexical trial
changes some candidate lists but adds no target hits. Both are rejected. Their
exact patches are retained as research inputs, never applied to production.

## Causal survival intervention

`prefix_survival_oracle.py` archives a fixed commit into a separate tree and
uses the known answer to append at most one already generated, exactly
continuable gold prefix after ordinary pruning. It never changes option
generation, completed-path cuts, confidence filters or final ranking. The
ordinary48 and existing reserves remain intact. Gold labels and the intervention
exist only in this tool's temporary Java copy, never in the app.

This optimistic diagnostic is not deployable accuracy or a formal maximum:
another tokenization, an omitted character or final-stage scoring can still
prevent the target from appearing. Its paired p-values are descriptive
diagnostics, not evidence about population typing accuracy.

With prefix protection on700 cases, first remains152, top5 rises280→283 and
top20 rises362→370. It intervenes on321 cases and adds2,829 prefixes across
pruning checkpoints. Thus even answer-assisted prefix protection only rescues
eight visible targets and no first choices. Merely widening this reserve is
unlikely to provide the large first-choice improvement needed for1.0.

Additional archive-only flags record whether the full target was ever
generated, survived the completed pool, passed confidence filtering and reached
the displayed20. The report distinguishes these losses instead of calling
every missing sentence a prefix-search error. With the intervention,175 targets
are cut from the completed pool,145 are ranked outside20, six fail confidence
filtering and four are not generated. These are intervention-arm counts, not a
breakdown of ordinary app errors. The observer-only control matches all700
baseline candidate lists byte for byte:

|Target outcome|Ordinary baseline|Answer-assisted prefix protection|
|---|---:|---:|
|Displayed|362|370|
|Not generated|232|4|
|Completed pool cut|31|175|
|Confidence filtered|0|6|
|Outside displayed20|75|145|

228 targets become generated and none lose generation, while only eight become
visible. The next useful model work should
examine complete-target score deficits and final-pool losses, alongside prefix
training; this experiment does not establish that ranking alone can solve all
remaining omissions.

## Reproduction

Activate the configured SDK/JDK first. All experimental Java lives below
`.native/`; the following commands do not patch the app working tree.

```sh
source /workspace/android-environment/activate.sh
PYTHONPATH=tools python -m unittest tools/test_prefix_retrieval.py tools/test_search_recovery.py tools/test_search_alignment.py
python tools/run_prefix_retrieval_trial.py lexical tools/reports/prefix-retrieval-2026-10-15/calibration700.tsv /tmp/lexical.tsv .native/reproduce-prefix-lexical
python tools/prefix_survival_oracle.py tools/reports/prefix-retrieval-2026-10-15/calibration700.tsv /tmp/oracle.tsv .native/reproduce-prefix-oracle
python tools/prefix_survival_oracle.py tools/reports/prefix-retrieval-2026-10-15/calibration700.tsv /tmp/control.tsv .native/reproduce-prefix-control --control
python tools/report_prefix_retrieval.py tools/reports/prefix-retrieval-2026-10-15/calibration700.tsv /tmp/control.tsv /tmp/oracle.tsv /tmp/comparison.json --diagnostics /tmp/oracle.diagnostics.tsv
```

Pinned public source caches allow new and historical data preparations to be
reproduced; see `prepare_prefix_retrieval.py`. The data tests skip that one
reproduction check explicitly if those source snapshots are unavailable.
Native comparisons validate input order, complete outputs, exact codes,
unique bounded candidate lists and target ranks. A disabled-intervention
control must match the baseline byte for byte. New tests also reject partial
or inconsistent diagnostic artifacts and changed instrumentation hooks.

11 Python checks pass with no skips; the final two artifact/diagnosis checks
also pass after adding an explicit observer-only report mode. The rejected
lexical patch reproduces20 complete native outputs. Adding terminal-stage flags
preserves all700 enabled-intervention candidate lists byte for byte. Since no
app or model changes remain, Gradle/lint, simulated Single and performance gates
are not rerun for delivery. The full result/hashes are retained in the
[work report](../tools/reports/prefix-retrieval-work-2026-10-15.json).
