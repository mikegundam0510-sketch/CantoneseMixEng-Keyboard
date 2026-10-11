# Tatoeba Cantonese experiment data

Text: © Tatoeba contributors, [CC BY 2.0 France](https://creativecommons.org/licenses/by/2.0/fr/).
The distributor states that some sentences additionally have a CC0 license; this
experiment conservatively treats the entire selected subset as CC BY 2.0 FR.

Obtained from Aaron H. K. Tan's [Jyut Dictionary release v4.25.0623](https://github.com/aaronhktan/jyut-dict/releases/tag/v4.25.0623-release),
`Jyut-Dictionary_4.25.0623_Windows_64bit_portable.zip`, member
`Jyut Dictionary/dict.db`. The Tatoeba source metadata in that database identifies
the snapshot as **2023-04-08**, with source URL https://tatoeba.org/eng/downloads.
This is a snapshot date, not the date of creation of every sentence.
Hashes are recorded in `manifest.json`; no executable in the archive is run.

Only `language = 'yue'` sentences joined through `sentence_links` to the exact
`Tatoeba—Cantonese-English` source are included. Other dictionary examples in the
same database are **not** licensed by this notice and are excluded. The original
database/archive is not committed to this repository or shipped with the app.

Upstream conversion: Jyut Dictionary can convert simplified input to traditional
Chinese using OpenCC. This project normalizes NFC and whitespace, filters and
groups examples, retains punctuation and English boundaries, and extracts Han
chunks for evaluation. The `id` and `links` fields retain redistributed database
record IDs for traceability; they are not asserted to be original Tatoeba IDs.
Contributor usernames, sentence dates, and original author groups are absent
from this distribution. Credit remains with Tatoeba's contributors; neither
Tatoeba nor Jyut Dictionary endorses this project.

These are community examples and translations, **not measured Hong Kong chat
frequency**, and can contain unnatural wording. The colloquial-marker filter
does not establish grammatical quality. Grouping limits leakage through shared
translations and near duplicates but cannot detect every paraphrase. Latin text
is preserved in JSONL; the existing character model resets at Latin/punctuation,
and its Han-chunk evaluation does not measure whole mixed-language sentences.

`protocol.json` freezes selection and acceptance before decoder evaluation.
`manifest.json` records the split, prior-corpus exclusions and checksums. Only
`train.jsonl` contributes counts; validation selects a weight, and heldout is
reserved for post-selection checks. Each family contributes each gram once.
