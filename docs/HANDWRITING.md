# Built-in offline handwriting (0.6.5)

The toolbar pen opens a native one-character ink pad in this input method. Candidates are confirmed manually; undo, clear, backspace, space, enter and return-to-keyboard controls remain within the app. Password and numeric editors disable handwriting. Input strokes are kept in memory only and cleared on candidate confirmation, editor change, keyboard dismissal and service destruction. No Internet permission, telemetry or handwriting history is added.

Recognition uses Zinnia's C++ classifier with the Tegaki 0.3 light Traditional Chinese model. The public model ships in the APK and is memory-mapped only when handwriting is opened. A build-time task fetches the versioned public model archive and retains its licence/readme/meta files in assets; the phone performs no model download. Source: taku910/zinnia revision 581faa8f6f15e4a7b21964be3a5ec36265c80e5b (BSD); Tegaki traditional-chinese-light release asset 2420209 (LGPL; notices accompany the model). Rebuilding requires Python 3 and build-host network access once, NDK 27.0.12077973 and CMake 3.22.1.

This is stroke-based single-character recognition. Correct stroke order and clear writing help; joined cursive writing, multi-character handwriting, uncommon Cantonese characters and unusual stroke orders require further acceptance/model work. No claim of full character coverage or Samsung-equivalent accuracy is made.

Automated Android checks draw a stroke and require a genuine 一 candidate, select it into the current editor, undo and clear further strokes, return to this keyboard, verify the IME identity remains unchanged, and repeat at cover/unfolded sizes. Physical Samsung touch/stylus quality and broader handwritten-character accuracy still require device trials.
