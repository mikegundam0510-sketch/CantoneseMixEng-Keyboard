# Structured ranking research data

These are diagnostic derivatives of the frozen, attributed TRAIN rows in
[`../joint_ranking/NOTICE.md`](../joint_ranking/NOTICE.md) and its original source
notices. Retain those full attribution records and licences when redistributing.
HKCanCor: CC BY 4.0; Tatoeba: CC BY 2.0 France; retained UD-derived material:
CC BY-SA 4.0; project-authored rows: repository licence. Mixed derived model
weights, if fitted, are offered under CC BY-SA 4.0, as for the retained models.

No words.hk examples or phone text train these comparisons. Dictionary examples
remain evaluation-only in the separately frozen joint-ranking data. No new
recordings, speakers or measured contemporary chat frequencies are claimed.

`gap/` records the original 1,044 missing TRAIN targets without a close observed
prefix pair. The outer files extend the audit to all 1,821 missing TRAIN targets.
Shadow positive paths use known TRAIN labels; they are supervised diagnostics,
never answer-free inference results. They are not included in the APK.

Audit columns (no header): source, context, code, gold, selected-option full path,
potential-option full path, present in completed 128 pool, generated before a
final cap, earliest observed total gold-prefix pruning position, number of omitted
segments in the chosen diagnostic path, diagnostic raw score, best actually
generated raw score, diagnostic `position:code:token:selected` segments, legal Han
full path. Empty/impossible scores use `-Infinity` only in the audit. Training
pair scores must be finite. Potential option eligibility is an upper bound,
not a guarantee that those tokens will be selected in any real context.

Reconstructed pair columns: source, context, full code, full gold, stage,
position, positive, actual negative, raw/final baseline offset, provenance.
Gold-derived paths are never inserted into the ordinary decode lattice. Visible
lists are ordinary inference and must exactly match the frozen baseline lists.
