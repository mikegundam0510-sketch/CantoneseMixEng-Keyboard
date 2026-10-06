#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .native app/build/generated/semanticAssets/licenses/semantic
if [ ! -d .native/llama/.git ]; then git clone https://github.com/ggml-org/llama.cpp.git .native/llama; fi
git -C .native/llama checkout d7a695ef679138c13d86359b84c1731d36213d32
cmake -S tools/semantic_probe_cmake -B .native/host -DLLAMA_SOURCE="$PWD/.native/llama" -DCMAKE_BUILD_TYPE=Release
cmake --build .native/host --target semantic-probe llama-quantize -j 2
if [ ! -f .native/qwen-q8.gguf ]; then
    curl --fail --location --retry 3 'https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/1eaf4d9657fe65ad10a51eab76a8db5b363bddaa/Qwen3-0.6B-Q8_0.gguf' -o .native/qwen-q8.gguf
fi
echo '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031  .native/qwen-q8.gguf' | sha256sum --check
model=app/build/generated/semanticAssets/semantic-model.gguf
if [ ! -f "$model" ]; then .native/host/bin/llama-quantize --allow-requantize .native/qwen-q8.gguf "$model" Q4_K_M; fi
sha256sum "$model" | cut -d ' ' -f 1 > app/build/generated/semanticAssets/semantic-model.sha256
cp .native/llama/LICENSE app/build/generated/semanticAssets/licenses/semantic/LLAMA-MIT.txt
curl --fail --location --retry 3 'https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/1eaf4d9657fe65ad10a51eab76a8db5b363bddaa/LICENSE' -o app/build/generated/semanticAssets/licenses/semantic/QWEN-APACHE-2.0.txt
