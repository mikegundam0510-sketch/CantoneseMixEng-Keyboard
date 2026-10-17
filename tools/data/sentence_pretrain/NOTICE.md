# Two-stage sentence-language experiment

This directory contains provenance, hashes, protocol and research weights.
The corpus/pair cache lives under ignored `.native/sentence-pretrain-20261017`.
It is not mirrored here. Follow the pinned download URL and SHA256 in
`source-audit.json`, then run `tools/prepare_sentence_pretrain.py` to reproduce it.

Common Voice contributors donated the Cantonese Sentence Collector prompts under
the CC0 public-domain dedication. Mozilla's official contribution terms and the
archived Sentence Collector's public-domain admission policy are pinned in
`source-audit.json`. The 9,444 source rows are read prompts with no contributor or
conversation IDs. They are not newly recorded Hong Kong conversations or measured
chat frequency. Near duplicates share a cluster; all prompts are TRAIN only.
Mozilla asks users not to mirror the dataset; raw and derived prompt text stays
out of Git. No audio, accounts, demographics or private messages are downloaded.

The existing attributed text/rivals retain the notices in
[clean_language_models](../clean_language_models/NOTICE.md),
[clean_ranking](../clean_ranking/NOTICE.md) and
[current_search](../current_search/NOTICE.md):

- HKCanCor: Kang Kwong Luke and May L. Y. Wong, CC BY 4.0; original 46 TRAIN
  conversation files only.
- Tatoeba contributors via Aaron H. K. Tan / Jyut Dictionary, snapshot2023-04-08,
  CC BY 2.0 France; original TRAIN translation families only.
- UD_Cantonese-HK: Wong, Gerdes, Leung and Lee, CC BY-SA 4.0; original custom
  TRAIN subset only.
- Project-authored and daily scenarios: repository licence; synthetic examples,
  not real-user usage frequencies.

The mixed derived research weights are offered under CC BY-SA 4.0; source
contribution licences and attribution continue to apply. Code retains the
repository code licence. Source authors do not endorse these modifications.
words.hk/NCDOL examples remain evaluation-only. SpiCE and CantoMap are documented
as investigated sources, but no data from either enters this experiment.

No frozen evaluation target or answer is used for fitting. Evaluation text is
read only to exclude full containment of spans of six or more characters,
including the reviewed-normalized forms. Internal validation holds out whole
original conversations, translation families and authored scenarios across both
training stages. This does not establish unseen-speaker validation for Common
Voice, whose author IDs are unavailable in the published sentence file.
