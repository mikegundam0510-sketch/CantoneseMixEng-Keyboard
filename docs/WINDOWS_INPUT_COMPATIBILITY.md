# Windows input compatibility — 0.6.20

The user's requirement is to retain the characters available in Windows Cangjie
and Quick. The proposed vocabulary-only reduction was withdrawn: the full
0.6.19 character inventory is retained, with all previous mappings and their
order unchanged. No unused-character filter is applied.

The app previously bundled Cangjie 5 codes. Append 6,124 previously missing
1–5-letter mappings from the pinned, MIT-licensed Cangjie3-Plus cj3.txt and
cj3-special.txt tables, including 面/mwyl, 捏/qhxm and 撐/qfbq. Existing
面/mwsl, 捏/qag and 撐/qfbh remain valid. The runtime derives Quick first/last
codes from both generations. Longer upstream x-prefixed disambiguation codes
are outside the app's five-letter Cangjie limit and are not imported.

Total: 103,942 distinct characters/symbols, 139,356 distinct character/code
pairs. Candidates remain available through scrolling/paging; no single-character
candidate cap is added. Dictionary tests check every bundled full and Quick
code and every full-code prefix, plus representative third/fifth-generation
and legacy variants.

`python3 tools/check_windows_character_coverage.py` exhaustively checks Python's
CP950 and Big5-HKSCS codecs: all 13,070 and 17,618 CJK characters respectively
are present. This verifies those legacy encoding repertoires, not the Windows
IME's individual codes or its Unicode extension configuration.

These are independent public tables, not an export of the original Microsoft
IME. Exact Windows parity has not been verified. Windows version, legacy/new
IME and enabled character sets can differ. A future reported missing character
and code should be tested against the actual Windows configuration before
adding a sourced compatibility mapping.

Version code 27 / 0.6.20 reuses the pinned 0.6.19 signing certificate and the
existing learning preference files. No learned history is cleared. Runtime
device upgrade and Windows-to-Android exhaustive comparison are unverified.

Validation: 96 JVM tests pass, with zero failures/errors/skips. Comparing with
e8586b0, 40 development cases retain top-1/top-5/top-8 counts of 33/39/39;
120 held-out cases retain 61/97/105. Run
`bash tools/context_accuracy.sh e8586b0 /tmp/cangjie-compatibility-evidence`.
The release APK builds and verifies against the existing pinned signer.
