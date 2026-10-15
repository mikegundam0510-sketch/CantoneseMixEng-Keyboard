# Displayed-candidate phrase relation model

`relation_ranker.b64` (PRR3) contains a modified train-only POS lexicon and fitted
weights. These derived lexicon/weights and their encoded model are offered under
CC BY-SA4.0, https://creativecommons.org/licenses/by-sa/4.0/ . The complete
license is retained in `CC-BY-SA-4.0.txt`. This attribution concerns these data
assets; it does not change the surrounding application's source license.

UD_Cantonese-HK: Tak-sum Wong, Kim Gerdes, Herman Leung and John Lee,
"Quantitative Comparative Syntax on the Cantonese-Mandarin Parallel Dependency
Treebank", Depling2017, pp266–275. Source:
https://github.com/UniversalDependencies/UD_Cantonese-HK at
68c3151c1181a7b67ef5c917570635bcccf7e4bf, CC BY-SA4.0.
Original source description and license are retained in `UD-README.md` and
`UD-LICENSE.txt`. Only the Missing Days and Temple interview training productions
contribute text/POS. The production-disjoint evaluation material does not train
this asset. This is a custom split, not an official UD benchmark result.

HKCanCor: Luke, K. K., & Wong, M. L. Y. (2015), The Hong Kong Cantonese Corpus,
https://github.com/fcbond/hkcancor , CC BY4.0,
https://creativecommons.org/licenses/by/4.0/ . Only the existing46 training
conversations contribute these pairs. The full HKCanCor license is also bundled.

Tatoeba contributors: https://tatoeba.org/ , CC BY2.0 France,
https://creativecommons.org/licenses/by/2.0/fr/ . The pinned Jyut Dictionary
source and attribution remain in the adjacent `tatoeba/NOTICE.txt`. The existing
training families contribute to this modification. Project-authored scenario
variants are synthetic, not measured Hong Kong usage frequency. Original authors
do not endorse this keyboard or these modifications.

The original2,165-feature tail model and POS lexicon remain intact. A separate
2,502-feature head map uses2,236 actual native first-choice repair/protection
pairs from the same5,381 training examples, with at least two source families
supporting a feature and65/20/15 corpus-source balancing. The fitted head map is
also a modification under the same CC BY-SA4.0 terms.

Tail corrections retain strength1/limit2; the head correction has strength1.5,
limit2, margin0.5 and minimum raw lift0.5. Only a supported existing displayed
candidate may move first, with the old first retained second. Ordered Chinese
numerals/ordinals and positive word/sequence/context personal preferences remain
protected. The PRR3 wrapper enables completed pool128; a zero-threshold/empty
head map can enable search alone. Older/missing models retain pool96. Dictionary
characters are not banned. Parameters, hashes and aggregate evaluation are in
`RELATION_RANKER_REPORT.json`.

words.hk NCDOL1.0 dictionary examples are evaluation-only development material;
they never train this model or POS lexicon and are not bundled in the APK.
The latest independent500-example comparison has108→109 first hits (two gains,
one loss), with198 top-five and256 top-twenty hits unchanged. Search-only has
no extra independent target hits. The paired first-hit p-value is1, giving very
limited evidence. These dictionary examples are not contemporary chat-frequency
or physical Fold7 evidence. No private messages or phone learning records train
this immutable model; existing personalization remains on the device.
