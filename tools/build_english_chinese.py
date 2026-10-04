"""Derive exact English gloss -> traditional Chinese candidates from supplied CC-CEDICT.
Run: python3 tools/build_english_chinese.py /path/to/cedict.gz
Derived dictionary is CC BY-SA 4.0; authored HK overrides are marked separately.
"""
import base64,gzip,pathlib,re,json,hashlib,math,sys
root=pathlib.Path(__file__).resolve().parents[1];assets=root/'app/src/main/assets'
source=pathlib.Path(sys.argv[1]);text=gzip.open(source,'rt',encoding='utf-8').read()
frequencies={}
for line in (assets/'character_frequencies.tsv').read_text().splitlines():
 f=line.split('\t')
 if len(f)==2 and not line.startswith('#'):frequencies[f[0]]=int(f[1])
index={}
for line in text.splitlines():
 m=re.match(r'^(\S+) \S+ \[.*?\] /(.*)/$',line)
 if not m:continue
 chinese,definitions=m.groups()
 if not re.fullmatch(r'[\u3400-\u9fff]{1,8}',chinese):continue
 score=round(sum(math.log1p(frequencies.get(ch,1)) for ch in chinese)/len(chinese)*100)-len(chinese)*10
 for gloss in definitions.split('/'):
  word=re.sub(r'\([^)]*\)','',gloss).strip().lower()
  word=re.sub(r'^(to |a |an |the )','',word).strip()
  if re.fullmatch(r"[a-z][a-z'-]{1,23}",word):index.setdefault(word,{})[chinese]=max(score,index.get(word,{}).get(chinese,0))
overrides=(root/'tools/english_chinese_hk.txt').read_text().splitlines()
for line in overrides:
 f=line.split()
 for rank,word in enumerate(f[1:]):index.setdefault(f[0],{})[word]=1000000-rank
rows=[]
for word,translations in sorted(index.items()):
 for chinese,weight in sorted(translations.items(),key=lambda p:(-p[1],p[0]))[:6]:rows.append(f'{word}\t{chinese}\t{weight}\n')
out=assets/'english_chinese.tsv';out.write_text('# CC-CEDICT-derived, CC BY-SA 4.0; see licenses/english-chinese. HK priorities are authored.\n'+''.join(rows))
out.with_suffix('.b64').write_bytes(base64.b64encode(gzip.compress(out.read_bytes(),mtime=0)))
notices=assets/'licenses/english-chinese';notices.mkdir(parents=True,exist_ok=True)
header='\n'.join(line for line in text.splitlines() if line.startswith('#'))
(notices/'SOURCE.txt').write_text(header+'\n\nDerived by tools/build_english_chinese.py: exact one-word glosses, traditional forms, six candidates maximum, frequency ranking; authored HK meanings override ranking.\nDerived data: CC BY-SA 4.0.\n')
(notices/'REPORT.json').write_text(json.dumps({'source':'https://www.mdbg.net/chinese/dictionary?page=cc-cedict','source_gzip_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'english_words':len(index),'candidates':len(rows)},indent=2)+'\n')
print('English words',len(index),'candidates',len(rows),'bytes',out.stat().st_size)
