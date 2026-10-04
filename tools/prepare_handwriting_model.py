"""Fetch the public, versioned training model at build time; runtime needs no network."""
import io,json,pathlib,urllib.request,zipfile,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
assets=root/'app/src/main/assets';model=assets/'handwriting-zh_TW.model'
url='https://github.com/tegaki/tegaki/releases/download/v0.3/tegaki-zinnia-traditional-chinese-light-0.3.zip'
if model.is_file() and (assets/'licenses/handwriting/MODEL.json').is_file():
    report=json.loads((assets/'licenses/handwriting/MODEL.json').read_text())
    if hashlib.sha256(model.read_bytes()).hexdigest()==report['sha256']:raise SystemExit(0)
req=urllib.request.Request(url,headers={'User-Agent':'CantoneseMixEng-model-builder'})
with urllib.request.urlopen(req,timeout=90) as response:data=response.read()
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    files=[n for n in archive.namelist() if n.endswith('/handwriting-zh_TW.model')]
    if len(files)!=1:raise RuntimeError('Traditional Chinese model missing')
    payload=archive.read(files[0]);assets.mkdir(parents=True,exist_ok=True);model.write_bytes(payload)
    notices=assets/'licenses/handwriting';notices.mkdir(parents=True,exist_ok=True)
    for name in archive.namelist():
        base=pathlib.PurePosixPath(name).name
        if base and (base.startswith(('README','COPYING','LICENSE','AUTHORS','LGPL')) or base.endswith('.meta')):
            (notices/base).write_bytes(archive.read(name))
    (notices/'MODEL.json').write_text(json.dumps({'source':url,'release_asset_id':2420209,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)},indent=2)+'\n')
(notices/'ZINNIA-BSD.txt').write_bytes((root/'app/src/main/cpp/zinnia/COPYING').read_bytes())
print('Bundled traditional model:',len(payload),'bytes')
