# Fold7 unfolded reference layout — 0.6.22

Match the user's supplied 133911.jpg key arrangement when split mode is active
(available width at least 600dp, full-hand layout, split setting enabled).

| Row | Left | Right |
|---|---|---|
| Numbers, when enabled | 12345 | 67890 |
| Top | QWERT | YUIOP |
| Home | ASDFG, with a small left indent | GHJKL |
| Lower | Shift, ZXCV | VBNM, Delete |

G and V deliberately appear on both halves; each copy invokes the same existing
letter handler. Delete retains repeat behavior and Shift retains caps-lock long
press. The bottom row becomes ?123, slash, globe, wide space, period, action
arrow. Space shows 速成/倉頡/English and retains cursor gestures. Period's long
press still opens punctuation choices, including commas. The arrow continues
to invoke the editor's existing enter/action behavior and exposes its action
name for accessibility.

Fold radical keys use lowercase Latin legends at the top right and centered
radicals; the T legend is 甘, as in the reference. Key codes remain unchanged.
The larger bottom row has pill-shaped mode/action keys and the action key uses
the configured accent. Cover-screen, single-hand, symbol and numeric layouts
retain their existing arrangements. Theme colors and optional number-row
settings remain available.

Release build and lint are checked; the APK keeps the persistent signer from
0.6.19 with version code 29. Fold7 real-device visual/touch validation has not
been performed. Check unfolding/folding while composing, both G/V copies,
delete repeat, Shift lock, space cursor gestures, punctuation long press,
accessibility action labels and entering/searching/sending in actual editors.

## 0.6.23 size and editing-icon refinement

The second supplied image, 133914.jpg, is used only for face-size proportions
and Shift/Backspace drawings. Its compact row arrangement and printed key
codes/letters are not adopted. Keep the split rows, duplicates, weights and
bottom-row controls introduced in 0.6.22.

Estimate the five-key half's letter face width after existing side padding,
center gap and key-face insets. Set its height to the reference ratio of roughly
140/110, bounded to 44–68dp before applying the user's height preference. At
700dp available width and default height preference this is about 55dp rather
than the previous 42dp. Number faces remain 92% of the letter height, with
larger number text; right-corner legends scale with face height. The bottom
row remains 4dp taller than letters.

Shift and Backspace use larger rounded-stroke outlines proportional to their
faces, with the hollow up arrow and left-pointing deletion frame plus X shown
in the reference. Caps-lock and deletion behavior are unchanged. Cover-screen
key heights retain their existing settings; editing-icon drawings apply in both
layouts. Version code 30 / 0.6.23 retains the pinned signer and learned data.
Release build and lint are checked; real Fold7 rendering remains unverified.
