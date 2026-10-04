"""Build an attributed, pinned offline five-stroke dictionary."""
import hashlib,json,pathlib,re,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
ASSETS=ROOT/'app/src/main/assets'
REV='1e8fff9b9494ddec23b0cbc526bcfd8171a6fd48'
SHA='b3e93dce89c185f45c3d6e189b86b3a8626913352cc85e1094c786579a665791'
BASE='https://raw.githubusercontent.com/rime/rime-stroke/'+REV+'/'
out=ASSETS/'stroke.tsv';notices=ASSETS/'licenses/stroke';report=notices/'SOURCE.json'
inputs_sha=hashlib.sha256((ASSETS/'cangjie5.base.dict.yaml').read_bytes()+(ASSETS/'character_frequencies.tsv').read_bytes()).hexdigest()
if out.is_file() and report.is_file():
    info=json.loads(report.read_text())
    if info.get('revision')==REV and info.get('inputs_sha256')==inputs_sha and info.get('output_sha256')==hashlib.sha256(out.read_bytes()).hexdigest():raise SystemExit(0)
def fetch(name):
    with urllib.request.urlopen(BASE+name,timeout=90) as response:return response.read()
source=fetch('stroke.dict.yaml')
if hashlib.sha256(source).hexdigest()!=SHA:raise RuntimeError('Stroke dictionary checksum mismatch')
allowed=set()
for line in (ASSETS/'cangjie5.base.dict.yaml').read_text().splitlines():
    f=line.split('\t')
    if len(f)>1 and len(f[0])==1 and re.fullmatch('[a-z]{1,5}',f[1]):allowed.add(f[0])
weights={}
for line in (ASSETS/'character_frequencies.tsv').read_text().splitlines():
    f=line.split('\t')
    if len(f)==2 and not line.startswith('#'):weights[f[0]]=int(f[1])
hk='係唔嘅咗喺佢哋嘢咁啲冇嚟啦喎睇返畀攞噉咩食飲'
for ch in hk:weights[ch]=max(weights.get(ch,0),25000)
records=set()
for line in source.decode().splitlines():
    f=line.split('\t')
    if len(f)>1 and f[0] in allowed and re.fullmatch('[hspnz]{1,64}',f[1]):records.add((f[0],f[1],max(1,weights.get(f[0],1))))
if len(records)<10000:raise RuntimeError('Incomplete stroke dictionary')
out.write_text('# Rime Stroke, LGPL-3.0; see licenses/stroke.\n'+''.join(f'{word}\t{code}\t{weight}\n' for word,code,weight in sorted(records)))
notices.mkdir(parents=True,exist_ok=True)
for name in ('LICENSE','AUTHORS','README.md'):(notices/name).write_bytes(fetch(name))
report.write_text(json.dumps({'inputs_sha256':inputs_sha,'source':BASE+'stroke.dict.yaml','revision':REV,'source_sha256':SHA,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'entries':len(records),'characters':len({r[0] for r in records}),'processing':'Single characters supported by bundled Cangjie dictionary; all regional stroke-code variants retained; existing character frequencies and authored HK priorities.'},indent=2)+'\n')
print('Bundled stroke dictionary:',len(records),'codes,',len({r[0] for r in records}),'characters,',out.stat().st_size,'bytes')

