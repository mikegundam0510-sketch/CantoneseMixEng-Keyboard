#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
teacher_root=/workspace/cantonese-teacher-environment
mkdir -p "$teacher_root"
if [ ! -x "$teacher_root/venv/bin/python" ]; then python3 -m venv "$teacher_root/venv"; fi
"$teacher_root/venv/bin/python" -m pip install --disable-pip-version-check \
  --require-hashes --only-binary=:all: --no-deps --no-cache-dir --retries 0 \
  -r tools/strong_teacher/requirements.lock
if [ ! -d "$teacher_root/llama.cpp/.git" ]; then
  git clone --no-checkout --filter=blob:none --single-branch \
    https://github.com/ggml-org/llama.cpp.git "$teacher_root/llama.cpp"
fi
git -C "$teacher_root/llama.cpp" checkout --detach d7a695ef679138c13d86359b84c1731d36213d32
test "$(git -C "$teacher_root/llama.cpp" rev-parse HEAD)" = d7a695ef679138c13d86359b84c1731d36213d32
test -z "$(git -C "$teacher_root/llama.cpp" status --porcelain)"
"$teacher_root/venv/bin/cmake" -S tools/strong_teacher -B "$teacher_root/build" -G Ninja \
  -DCMAKE_MAKE_PROGRAM="$teacher_root/venv/bin/ninja" \
  -DLLAMA_SOURCE="$teacher_root/llama.cpp" -DCMAKE_BUILD_TYPE=Release
"$teacher_root/venv/bin/cmake" --build "$teacher_root/build" \
  --target teacher-likelihood llama-server test-gbnf-validator -j 2
# No automatic weight download, persistent server or APK packaging.
"$teacher_root/build/bin/llama-server" --version
