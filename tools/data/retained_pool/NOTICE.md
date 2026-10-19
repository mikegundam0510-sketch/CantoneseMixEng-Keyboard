# Complete-pool retention and new-character supplementation

Code is GPL-3.0-or-later. `expanded_generator.b64` is an exact numerical export
of the frozen expanded weights at
[`../vocabulary_expansion/models/expanded.npz`](../vocabulary_expansion/models/expanded.npz).
The weights are modified derivatives of the original direct-code teacher under
CC BY-SA4.0. Full terms remain in
[`licenses/sentence-language/CC-BY-SA-4.0.txt`](../../../app/src/main/assets/licenses/sentence-language/CC-BY-SA-4.0.txt).
No additional training, vocabulary selection or source collection occurs here.

Retain all attributions and dictionary code-fact licences in
[`../vocabulary_expansion/NOTICE.md`](../vocabulary_expansion/NOTICE.md),
[`../code_generator/NOTICE.md`](../code_generator/NOTICE.md) and the original
[`sentence-pretrain source audit`](../sentence_pretrain/source-audit.json).
Sources include HKCanCor (Luke/Wong, CC BY4.0), Tatoeba contributors via Aaron
H. K. Tan/Jyut Dictionary (2023 snapshot, CC BY2.0 France), UD Cantonese-HK
(Wong/Gerdes/Leung/Lee, CC BY-SA4.0), project-authored synthetic examples and
Mozilla Common Voice Sentence Collector donations (CC0 read prompts, TRAIN
only). Source contributors do not endorse this modified model. Read-prompt
counts are not measured private typing frequency. Raw/derived Common Voice
views remain ignored, not committed or bundled.

Known and reserved public words.hk examples are credited to Hong Kong
Lexicography Limited under NCDOL1.0. They are evaluation only, never used for
training or included in the app. Preserve full terms and attribution in
[`../daily_prefix/NOTICE.txt`](../daily_prefix/NOTICE.txt) and
[`../daily_prefix/LICENSE.txt`](../daily_prefix/LICENSE.txt).
The new500 source, family exclusions and provenance were fixed in the preceding
vocabulary experiment. Its use is recorded by this study's qualification and
reserve-started files, never described as unseen again after inference begins.

No private phone learning records are collected. Model and policy work does not
change local storage formats, stable APK signing, application identity or layout.
