# Context-search evaluation and search-policy experiment

New validation150 and heldout500 contain modified public examples from
粵典 words.hk, dictionary CSV SHA256
`31c55697f459564312e958bc87d077855b85c6965bab1a683c54d6ce6b6d5ddb`.
Original IDs, examples, headword/duplicate-family groups and source text are
retained in the companion JSONL files. Credit remains with words.hk and its
contributors; they do not endorse the project or modifications.

These examples are NCDOL1.0 **evaluation-only**. The complete source credit,
licence, conversion and redistribution terms remain in
[`../daily_prefix/NOTICE.txt`](../daily_prefix/NOTICE.txt) and its linked licence.
Examples never fit a model, enter a vocabulary, or ship as APK assets.

The source extractor's established punctuation/comma/lookup-mark normalization
is retained, then examples are selected by family/hash before any decoder
outcomes. This does not recode previous evaluation answers. All previously used
families, tracked target containment6+, and the complete cleaned primary TRAIN
spans (including reviewed-normalized variants) are excluded. This is another
family-separated public dictionary sample, not newly collected phone typing.

Old500/800/3893 outputs are observed calibration/guards. Their original
HKCanCor CC BY4.0, Tatoeba CC BY2.0 France, UD_Cantonese-HK CC BY-SA4.0,
project-authored and words.hk NCDOL attributions remain in the respective source
notices, especially `../joint_ranking/NOTICE.md`,
`../clean_language_models/NOTICE.md` and `../phrase_relations/NOTICE.md`.

Search policies change no trained model, dictionary character, code or lexical
asset. They use existing scores to keep bounded alternative paths. Archive-only
diagnostics observe old labels after/alongside unchanged ordinary decisions;
reconstructed paths never enter inference and no training pairs are emitted.
