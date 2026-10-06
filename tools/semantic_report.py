import json, statistics, sys
from pathlib import Path
cases = json.loads(Path(sys.argv[1]).read_text())
lines = Path(sys.argv[2]).read_text().splitlines()
assert len(cases) == len(lines)
base = ranked = available = fallbacks = 0
latencies = []; records = []
for case, line in zip(cases, lines):
    fields = line.split('\t'); latency = int(fields[0]); logits = list(map(float,fields[1:]))
    candidates = case['candidates']; expected = case['expected']
    base += candidates[0] == expected; available += expected in candidates
    # Conservative promotion; retain the decoder when classifier evidence is tied.
    chosen = max(range(len(logits)),key=logits.__getitem__) if len(logits)==len(candidates) else 0
    if logits and logits[chosen] - logits[0] < 1.0: chosen = 0
    fallbacks += len(logits) != len(candidates); ranked += candidates[chosen] == expected
    latencies.append(latency)
    records.append({**case,'selected':candidates[chosen],'logits':logits,'milliseconds':latency})
summary = {'cases':len(cases),'baseline_top1':base,'semantic_top1':ranked,
           'target_available':available,'fallbacks':fallbacks,
           'latency_median_ms':statistics.median(latencies), 'latency_max_ms':max(latencies),
           'hardware_note':'GitHub Linux CPU runner; these are NOT Android or Fold 7 latency measurements.'}
Path(sys.argv[3]).write_text(json.dumps({'summary':summary,'records':records},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
