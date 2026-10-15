# Training and evaluation

The two experimental tail-only models derive from the fixed5,381 licensed
phrase-relations training rows and train-only POS lexicon. Only47 of those rows
have targets in positions21–36; these models have limited independent training
support (41 families). The encoded models, fitted weights and derived lexicon
are offered under CC BY-SA4.0. Full license/attribution are retained in
[relations](../../../app/src/main/assets/licenses/relations/README.md),
[CC-BY-SA4.0](../../../app/src/main/assets/licenses/relations/CC-BY-SA-4.0.txt)
and [training sources](../phrase_relations/NOTICE.md).

HKCanCor: Luke and Wong(2015), CC BY4.0; UD_Cantonese-HK: Wong, Gerdes,
Leung and Lee(2017), revision68c3151c1181a7b67ef5c917570635bcccf7e4bf,
CC BY-SA4.0; Tatoeba contributors, CC BY2.0 France; project-authored scenarios
are synthetic. Original authors do not endorse these modifications.

All words.hk dictionary examples remain NCDOL1.0 evaluation-only material;
see [full notice/license](../daily_prefix/NOTICE.txt). Neither dictionary
examples nor phone learning data train these models or enter APK assets.
Previously observed evaluation rows are calibration. The 500 cases in
`../prefix_retrieval/heldout.tsv` were unopened when selection was frozen;
they have now been evaluated and cannot serve as an untouched test again.
The candidate had no independent target-hit gain and is not bundled in the app.
