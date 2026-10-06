# Contextual candidates and dictionary completion

The offline decoder now uses count-calibrated phrase evidence from all bundled
vocabulary, including phrases crossing token boundaries. Bounded lexical
lookahead protects earlier ambiguities during beam pruning. Complete words
receive a bounded frequency prior and compete by score with composed sentences,
instead of occupying the first five positions unconditionally.

The dictionary keeps the original Rime mappings and appends pinned MIT-licensed
HK completion mappings. It contains 133,232 distinct character/code pairs and
103,942 characters and symbols. All valid full codes, their prefixes and derived
Quick codes were checked for reachability. New CJK characters are classified
through Extension J even on older Java/Android Unicode tables, preventing them
from incorrectly receiving a zero non-Han language score.

Compact reverse-code strings and a sorted full-code prefix index reduce the
desktop Java loading benchmark heap from about 153 MB to 121 MB compared with
the same expanded dictionary using the original indexes. This is a JVM
measurement, not an Android device RAM measurement.

## Validation

- Actual JUnit 4.13.2: 76 tests passed across dictionary, decoder/model, Chinese
  repairs, mixed input, English translations, suggestions, stroke, clipboard,
  emoji and voice-policy classes. Android-dependent InputPolicy tests are left
  to the Android build.
- Every bundled full mapping and its prefixes, plus every derived Quick lookup,
  were checked. Samples include 㗎/rkrd, 𠝹/wlln, 𮯼 and Extension J characters.
- Examples include 收工又可以踩單車, 我想打電話, 我想買股票,
  我想睇電影, 我想修理單車, 收工又可以飲咖啡 and 收工又可以搭巴士.
- Generic corpus evidence is tested with the authored HK list absent. Modern
  CJK scoring, supplementary-character context, punctuation reset, exact source
  mappings and alternative candidates are covered.
- Persistent-key restoration is repeatable and rejects absent secrets or a
  certificate different from the pinned signer. All six workflow YAML files
  were parsed and checked for the restore step.

Candidate ranking remains dependent on the offline model and vocabulary; this
does not guarantee perfect interpretation of every novel sentence. Very recent
characters may display as missing glyphs on devices without a matching font.
Full Android build, lint and device acceptance must be reported separately.
