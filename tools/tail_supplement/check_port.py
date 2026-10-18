"""Check mathematical export before rerunning full native ordinary lists."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys
from study import ROOT,DATA,WORK,REPORTS,sha,write,verify
sys.path.insert(0,str(ROOT/'tools/code_generator'))
from model import load,Codec,decode


def prepare():
    verify();stage=WORK/'candidate'
    freeze=json.loads((DATA/'port-freeze.json').read_text())
    for name,wanted in freeze['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Port source changed: '+name)
    paths=[Path(__file__).parent/name for name in ('GeneratorCheck.java','IntegratedEvaluation.java')]
    subprocess.run(['javac','-encoding','UTF-8','-sourcepath',str(stage/'app/src/main/java'),'-d',str(stage/'classes')]+[str(p) for p in paths],check=True)
    values,chars=load(ROOT/'tools/data/code_generator/models/teacher.npz')
    codec=Codec(chars,json.loads((ROOT/'tools/data/code_generator/codes.json').read_text()))
    # Public TRAIN observations, not target-based error selection.
    rows=(ROOT/'tools/data/prefix_language/observation-cases.tsv').read_text().splitlines()[:80]
    pairs=[(f[1],f[2]) for f in (row.split('\t') for row in rows)]
    pairs += [('English😀你今日','OFONAOVRMRQ'),('你今日😀','a'),('','zz'),('','123'),('','a'*49)]
    with (WORK/'parity.tsv').open('x') as out:
        for context,code in pairs:
            results=decode(values,codec,code,context)
            out.write('\t'.join([context,code,'|'.join(t for t,s in results),'|'.join(repr(s) for t,s in results)])+'\n')
    raw=gzip.decompress(base64.b64decode((DATA/'code_generator.b64').read_bytes()));bad=WORK/'corrupt';bad.mkdir()
    samples=[]
    for i in range(8):
        value=bytearray(raw);value[4*i:4*i+4]=struct.pack('>i',-1);samples.append(bytes(value))
    samples += [raw[:-1],raw+b'X',b'bad',raw[:40]]
    cp=bytearray(raw);cp[32:36]=struct.pack('>i',0);samples.append(bytes(cp))
    # Locate the first parameter after the variable-length legal-code facts.
    at=32
    for i in range(2248):
        n=raw[at+4];at+=5
        for j in range(n):length=struct.unpack('>H',raw[at:at+2])[0];at+=2+length
    for value in (float('nan'),float('inf')):
        modified=bytearray(raw);modified[at:at+4]=struct.pack('>f',value);samples.append(bytes(modified))
    for i,sample in enumerate(samples):
        (bad/f'{i:02}.b64').write_bytes(base64.b64encode(gzip.compress(sample,mtime=0)))
    result=subprocess.check_output(['java','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.GeneratorCheck',
        str(DATA/'code_generator.b64'),str(WORK/'parity.tsv'),str(bad)],text=True)
    (REPORTS/'generator-parity.txt').write_text(result);print(result.strip())
    inputs=(WORK/'inputs.tsv').read_text().splitlines()+(WORK/'guard-inputs.tsv').read_text().splitlines()
    for part in range(4):
        (WORK/f'full-inputs-{part}.tsv').write_text(''.join(row+'\n' for row in inputs[part::4]))
    paths += [Path(__file__)]+sorted((stage/'classes').rglob('*.class'))
    paths += sorted((stage/'app/src/main/java').rglob('*.java'))+[stage/'app/src/main/assets/code_generator.b64']
    write(DATA/'native-freeze.json',dict(sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        test='85 Python/Java ordered+score comparisons and15 corrupt-model checks. Before full native known evaluation.'))


def run(part):
    verify()
    for name,wanted in json.loads((DATA/'native-freeze.json').read_text())['sha256'].items():
        if sha(ROOT/name)!=wanted:raise ValueError('Native port changed: '+name)
    stage=WORK/'candidate';out=WORK/f'full-output-{part}.tsv'
    if out.exists():raise ValueError('Preserve full native output')
    subprocess.run(['java','-Xmx1g','-cp',str(stage/'classes'),'hk.cantonesemixeng.keyboard.IntegratedEvaluation',
        str(stage/'app/src/main/assets'),str(WORK/f'full-inputs-{part}.tsv'),str(out)],check=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--part',type=int,choices=range(4));a=p.parse_args()
    if a.mode=='prepare':prepare()
    elif a.part is None:p.error('--part required')
    else:run(a.part)
