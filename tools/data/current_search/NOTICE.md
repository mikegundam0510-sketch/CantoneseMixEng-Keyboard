# Current-parent prefix/final training comparisons

These are modified derivatives of the 7,891 already attributed, code-admitted
TRAIN spans in [clean_ranking](../clean_ranking/NOTICE.md). Original raw text,
source IDs, conversation/translation families and normalization provenance remain
in that dataset. The current decoder is run anew to obtain actual competitors;
these are not newly collected private messages or contemporary frequency counts.

- HKCanCor: Kang Kwong Luke and May L. Y. Wong (2015), CC BY 4.0, the original
  46 training conversations only.
- Tatoeba contributors via Aaron H. K. Tan / Jyut Dictionary, snapshot
  2023-04-08, CC BY 2.0 France; frozen training translation families only.
- UD_Cantonese-HK: Wong, Gerdes, Leung and Lee, CC BY-SA 4.0, the retained custom
  training subset only.
- Project-authored/daily templates: repository licence; synthetic supervision,
  not measured usage frequency.
- Dictionary and candidate text retain the original attributions in
  [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md).

Full source notices and licence texts are linked from the clean-ranking notice.
Source authors do not endorse these modifications. Derived mixed training data
and research weights are offered under CC BY-SA 4.0; original source contribution
licences continue to apply. Code retains the repository code licence.

Each `pairs.jsonl.gz` row is `[stage, family, context, consumed_code, positive,
negative, current_raw_or_final_margin, origin]`. Origins distinguish actual lost
prefixes, survived prefix protection, ordinary final pools and separately audited
TRAIN-only legal shadow paths. Reconstructed positives never enter normal search.
Multiple rivals for a case do not count as independent source support.
`shadow/` retains the 120 separately reconstructed TRAIN traces, ordinary output
lists and 759 pre-deduplication comparisons. Their column definitions follow
[structured_ranking/NOTICE.md](../structured_ranking/NOTICE.md). Their exact
hashes are pinned in this dataset's manifest.

words.hk examples remain evaluation-only under their existing NCDOL 1.0 notices.
No dictionary example fits these weights or enters the Android asset directory.
No phone editor text or personal learning record is collected. The existing
context-search reserve500 remains unused until a selected model qualifies.
