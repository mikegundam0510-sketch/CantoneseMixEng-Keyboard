# Device acceptance checklist

Automated checks do not replace these device tests. Samsung-specific behaviour is unverified until tested on the target phone.

- Enable IME, select it, type in the app test field, Samsung Notes, a browser, and a messaging app.
- Quick: `of` includes 你, `vd` includes 好, `ha` includes 香, `eu` includes 港. Check Space chooses the first candidate, taps choose another, and raw-English button commits the code.
- Cangjie: disable Quick; `onf` includes 你. Disable Cangjie and verify `onf` no longer produces 你.
- Pick a non-first Chinese candidate repeatedly. Re-enter the same code, close/reopen keyboard, restart app: chosen character should move forward and persist. Clear learning: restore default ranking. Disable learning: use default ranking without deleting saved history.
- Test an editor with `IME_FLAG_NO_PERSONALIZED_LEARNING`: no personalised ordering and no new learning. Check text, visible-text, web, and numeric password variations: no candidates and no new learning.
- English `hello`, mixed uppercase, unknown names; symbols and Emoji; candidate paging for `mm`; shift tap and long-press; repeated Backspace; selected text replacement; emoji surrogate-pair deletion.
- Start composition then tap in another part of text: old candidates disappear and no stale composition is inserted. Switch apps, hide keyboard, open settings, rotate screen while composing.
- Verify multiline Return vs Search / Next / Done / Send. First Return during composition commits literal code without sending a message.
- Email and URL fields default to direct English. Numeric and phone fields show numeric layout. Confirm browser and custom editors accept input.
- Drag space left/right, including cancellation: move cursor without adding a space. Hold delete then close keyboard: repeat must stop.
- Dark / light / system themes, number row, 3 key heights, both single-hand modes, landscape. Test Samsung gesture and button navigation, increased display/font size, split screen, and Fold cover/inner screens if available.
- Target device: Galaxy Z Fold7 on One UI 8.5 (user-provided configuration). Check automatic split letter rows on the inner display (available width >= 600dp), normal rows on the cover display, split toggle off, and single-hand override. Fold/unfold with keyboard visible and during composition; verify no stale candidates or lost committed text. Multiwindow should follow the available width, not the physical screen size.
- TalkBack: keys have spoken labels; candidate selection, Space and Delete have click actions.
- AI instructions: keyboard picker works. On compatible Samsung device, manually select text and check for Galaxy AI; no claim that the keyboard directly invokes Samsung AI.
- Airplane mode: Chinese and English lookup still work. Check app permissions: no network / audio / accessibility permission. Verify no personal text is printed in logs.
