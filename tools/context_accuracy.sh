#!/usr/bin/env bash
set -euo pipefail
base=${1:-0bff053}
out=${2:-context-evidence}
mkdir -p "$out"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git archive "$base" app/src/main/assets app/src/main/java/hk/kaiboard/android | tar -x -C "$tmp"
for variant in before after; do
  root=.
  if [ "$variant" = before ]; then root="$tmp"; fi
  mkdir -p "$tmp/$variant-classes"
  java com.sun.tools.javac.Main -d "$tmp/$variant-classes" "$root"/app/src/main/java/hk/kaiboard/android/{DictionaryEngine,OfflineLanguageModel,QuickDecoder,SemanticPrompt}.java tools/ContextAccuracy.java
  for suite in development heldout; do
    cases=tools/semantic_cases.tsv
    if [ "$suite" = heldout ]; then cases=tools/lm_heldout_cases.tsv; fi
    java -cp "$tmp/$variant-classes" hk.kaiboard.android.ContextAccuracy "$root/app/src/main/assets" "$cases" "$suite" > "$out/$variant-$suite.jsonl"
  done
done
python3 - "$out" <<'PY'
import json, statistics, sys
from pathlib import Path
out=Path(sys.argv[1]); summary={}
for suite in ['development','heldout']:
    group={}; rows={}
    for variant in ['before','after']:
        records=[json.loads(s) for s in (out/f'{variant}-{suite}.jsonl').read_text().splitlines()]
        rows[variant]=records
        latencies=sorted(r['milliseconds'] for r in records)
        group[variant]={'cases':len(records),'top1':sum(r['candidates'][:1]==[r['expected']] for r in records),
          'top5':sum(r['expected'] in r['candidates'][:5] for r in records),
          'top8':sum(r['expected'] in r['candidates'][:8] for r in records),
          'available':sum(r['expected'] in r['candidates'] for r in records),
          'host_median_ms':statistics.median(latencies),'host_p95_ms':latencies[int(.95*(len(latencies)-1))]}
    group['changes']=[{'context':b['context'],'expected':b['expected'],'before':a['candidates'][:5],'after':b['candidates'][:5]}
      for a,b in zip(rows['before'],rows['after']) if a['candidates'][:5]!=b['candidates'][:5]]
    summary[suite]=group
summary['scope']='Development cases informed tuning. Held-out corpus cases are separate. Host JVM timings do not establish device fluency or full sentence understanding.'
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
for suite in ['development','heldout']:
    print(suite, {k:v for k,v in summary[suite].items() if k!='changes'})
    assert summary[suite]['after']['top1'] >= summary[suite]['before']['top1'], 'Top-1 regression'
PY
