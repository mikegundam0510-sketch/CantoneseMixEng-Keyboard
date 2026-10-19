"""Resolve public provenance and LFS SHA before downloading any teacher weights."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from prepare import DATA,ENV,write

BASE='Qwen/Qwen3-4B-Instruct-2507'
QUANT='unsloth/Qwen3-4B-Instruct-2507-GGUF'


def fetch(url):
    # Use the configured HTTPS proxy and ordinary CA verification. This code
    # never extracts credentials, disables TLS or tries an alternate proxy.
    with urllib.request.urlopen(url,timeout=60) as response:return response.read()


def resolve():
    base=json.loads(fetch('https://huggingface.co/api/models/'+BASE+'?blobs=true'))
    quant=json.loads(fetch('https://huggingface.co/api/models/'+QUANT+'?blobs=true'))
    for expected,item in ((BASE,base),(QUANT,quant)):
        if item.get('id')!=expected or item.get('gated') or item.get('disabled'):
            raise ValueError('Expected the fixed public, non-gated model')
        if not re.fullmatch('[0-9a-f]{40}',item.get('sha','')):raise ValueError('Missing fixed source revision')
        if item.get('cardData',{}).get('license')!='apache-2.0':raise ValueError('Review model licence before use')
    siblings=[x for x in quant['siblings'] if x['rfilename'].endswith('Q4_K_M.gguf')]
    if len(siblings)!=1:raise ValueError('Expected one unsharded Q4_K_M file; do not guess a substitute')
    item=siblings[0];lfs=item.get('lfs',{});digest=lfs.get('sha256',lfs.get('oid','')).removeprefix('sha256:')
    if not re.fullmatch('[0-9a-f]{64}',digest) or not 0<lfs.get('size',0)<4*2**30:
        raise ValueError('Missing authoritative bounded LFS SHA/size')
    licence=fetch(f'https://huggingface.co/{BASE}/resolve/{base["sha"]}/LICENSE')
    if b'Apache License' not in licence or b'Version 2.0' not in licence:raise ValueError('Unexpected source licence text')
    # Keep source/model cards with the precise revisions; no model outputs yet.
    files={
        'model-base-card.md':fetch(f'https://huggingface.co/{BASE}/resolve/{base["sha"]}/README.md'),
        'model-quant-card.md':fetch(f'https://huggingface.co/{QUANT}/resolve/{quant["sha"]}/README.md'),
        'MODEL-APACHE-2.0.txt':licence}
    for name,content in files.items():
        with (DATA/name).open('xb') as out:out.write(content)
    write(DATA/'model-source.json',dict(base_id=BASE,base_revision=base['sha'],quant_id=QUANT,
        quant_revision=quant['sha'],filename=item['rfilename'],sha256=digest,bytes=lfs['size'],
        url=f'https://huggingface.co/{QUANT}/resolve/{quant["sha"]}/{item["rfilename"]}',
        licence='Apache-2.0',licence_sha256=hashlib.sha256(licence).hexdigest(),
        provenance_resolved_before_outputs=True,
        limitation='A multilingual candidate teacher, not yet a validated Cantonese accuracy improvement'))
    print('Public model provenance resolved; weights not downloaded')


def download():
    source=json.loads((DATA/'model-source.json').read_text());folder=ENV/'models';folder.mkdir(exist_ok=True)
    output=folder/'teacher-q4_k_m.gguf';pending=folder/'teacher-q4_k_m.partial'
    if pending.exists() or output.exists():raise ValueError('Preserve existing download; verify before reusing')
    digest=hashlib.sha256();size=0
    with urllib.request.urlopen(source['url'],timeout=120) as response,pending.open('xb') as out:
        while True:
            block=response.read(2**20)
            if not block:break
            size+=len(block)
            if size>source['bytes']:raise ValueError('Model exceeds authoritative size')
            digest.update(block);out.write(block)
    if size!=source['bytes'] or digest.hexdigest()!=source['sha256']:
        raise ValueError('LFS checksum/size mismatch; do not use the partial model')
    pending.rename(output)
    write(DATA/'model-download.json',dict(path=str(output),sha256=digest.hexdigest(),bytes=size,
        authoritative_lfs_match=True,teacher_inference_run=False))
    print('Exact LFS size/SHA verified; model evaluation is still unrun')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['resolve','download']);a=p.parse_args()
    {'resolve':resolve,'download':download}[a.mode]()
