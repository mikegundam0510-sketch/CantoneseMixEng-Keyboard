# Stronger teacher diagnostic preparation

Repository tools remain GPL-3.0-or-later. The separately installed llama.cpp
runtime is MIT, pinned to d7a695ef679138c13d86359b84c1731d36213d32;
its source licence is retained in the installed dependency checkout.
CMake/Ninja wheels use the exact official PyPI hashes in the requirements lock.

Dictionary code facts derive from the existing bundled dictionary, retaining
all GPL/LGPL/MIT contribution terms in app/src/main/assets/licenses/. Exported
full facts stay in ignored work storage; no dictionary entries are added or
removed by this preparation.

The cold60 diagnostic is sampled from the already consumed words.hk500,
credited to Hong Kong Lexicography Limited under NCDOL1.0. Preserve full terms
and attribution in ../daily_prefix/NOTICE.txt and ../daily_prefix/LICENSE.txt.
These are evaluation examples, never model training or APK assets. The32
controlled contexts derive from existing project-authored test sentences;
their exact alignment cuts are recorded in context-provenance.json.
No phone history or private chat data is collected.

No external teacher weights have been downloaded or run yet. The multilingual
Qwen3-4B-Instruct-2507 base and Unsloth Q4_K_M export are offered under Apache2.0;
the public cards, exact source revisions, expected LFS SHA and source licence
have now been resolved and preserved in this directory. Full terms are in
MODEL-APACHE-2.0.txt. Original model/source contributors do not endorse this
diagnostic. Weight-byte checksum and actual inference remain unverified while
the CDN is blocked. This preparation claims neither Cantonese accuracy
improvement nor a model ready for app distribution.
