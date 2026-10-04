"""Bundle checksum-pinned public handwriting models; no runtime network or ink collection."""
import io,json,pathlib,urllib.request,zipfile,hashlib
from build_handwriting_shapes import build
root=pathlib.Path(__file__).resolve().parents[1]
assets=root/'app/src/main/assets';model=assets/'handwriting-zh_TW.model';shapes=assets/'handwriting-shapes.bin'
notices=assets/'licenses/handwriting';report_file=notices/'MODEL.json'
MODEL_SHA='cd47f16b64e7ecaa4c2813d0f98231dfea7b411f48be1ead5c9b2eeb19330b11'
GLYPH_SHA='7bc5b7fc3da815dc2f51fa72a6c68c089af38f894da970ee82313d78b39b085e'
MODEL_URL='https://github.com/tegaki/tegaki/releases/download/v0.3/tegaki-zinnia-traditional-chinese-0.3.zip'
GLYPH_URL='https://codeload.github.com/chanind/hanzi-writer-data/zip/68d10a4b21150cae5e1ebbd223eed289cf32d90c'
if model.is_file() and shapes.is_file() and report_file.is_file():
    report=json.loads(report_file.read_text())
    if hashlib.sha256(model.read_bytes()).hexdigest()==MODEL_SHA and hashlib.sha256(shapes.read_bytes()).hexdigest()==report.get('shapes_sha256'):raise SystemExit(0)
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'CantoneseMixEng-model-builder'})
    with urllib.request.urlopen(req,timeout=120) as response:return response.read()
archive=zipfile.ZipFile(io.BytesIO(fetch(MODEL_URL)))
payload=archive.read(next(n for n in archive.namelist() if n.endswith('/handwriting-zh_TW.model')))
if hashlib.sha256(payload).hexdigest()!=MODEL_SHA:raise RuntimeError('Unexpected full model checksum')
glyph_data=fetch(GLYPH_URL)
if hashlib.sha256(glyph_data).hexdigest()!=GLYPH_SHA:raise RuntimeError('Unexpected glyph data checksum')
assets.mkdir(parents=True,exist_ok=True);notices.mkdir(parents=True,exist_ok=True);model.write_bytes(payload)
build(archive.read(next(n for n in archive.namelist() if n.endswith('/handwriting-zh_TW.xml'))),shapes,io.BytesIO(glyph_data))
for name in archive.namelist():
    base=pathlib.PurePosixPath(name).name
    if base and (base.startswith(('README','COPYING','LICENSE','AUTHORS','LGPL')) or base.endswith('.meta')):(notices/base).write_bytes(archive.read(name))
glyphs=zipfile.ZipFile(io.BytesIO(glyph_data))
for name in glyphs.namelist():
    path=pathlib.PurePosixPath(name)
    if len(path.parts)==2 and path.name in ('ARPHICPL.TXT','README.md','COPYING'):(notices/('GLYPH-'+path.name)).write_bytes(glyphs.read(name))
(notices/'ZINNIA-BSD.txt').write_bytes((root/'app/src/main/cpp/zinnia/COPYING').read_bytes())
report_file.write_text(json.dumps({'source':MODEL_URL,'sha256':MODEL_SHA,'bytes':len(payload),'glyph_source':GLYPH_URL,'glyph_archive_sha256':GLYPH_SHA,'shapes_sha256':hashlib.sha256(shapes.read_bytes()).hexdigest(),'shapes_bytes':shapes.stat().st_size},indent=2)+'\n')
print('Bundled full traditional model and order-independent shapes:',len(payload),shapes.stat().st_size)
