import zipfile,xml.etree.ElementTree as E,struct,math,pathlib,json
def raster(strokes):
    points=[(s,int(p.get('x')),int(p.get('y'))) for s,stroke in enumerate(strokes) for p in stroke]
    if not points:return []
    xs=[p[1] for p in points];ys=[p[2] for p in points];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;scale=24/max(1,max(xs)-min(xs),max(ys)-min(ys))
    ink=set();previous=-1;px=py=0
    for s,x,y in points:
        x=max(0,min(31,math.floor((x-cx)*scale+16)));y=max(0,min(31,math.floor((y-cy)*scale+16)))
        if s==previous:
            steps=max(abs(x-px),abs(y-py))
            for t in range(steps+1):
                xx=math.floor(px+(x-px)*t/steps+.5) if steps else x;yy=math.floor(py+(y-py)*t/steps+.5) if steps else y
                ink.add(yy*32+xx)
        else:ink.add(y*32+x)
        previous=s;px=x;py=y
    return sorted(ink)
def build(xml,output,glyph_archive=None):
    root=E.fromstring(xml);records=[]
    for ch in root.iter('character'):
        word=ch.findtext('utf8');strokes=ch.findall('strokes/stroke');pixels=raster(strokes)
        if word and len(word)==1 and pixels and 0<len(strokes)<=48:
            label=word.encode();records.append(label.ljust(16,b'\0')+struct.pack('<HH',len(strokes),len(pixels))+struct.pack('<'+'H'*len(pixels),*pixels))
    if glyph_archive:
        allowed={ch.findtext('utf8') for ch in root.iter('character')}
        glyphs=zipfile.ZipFile(glyph_archive)
        for name in sorted(glyphs.namelist()):
            path=pathlib.PurePosixPath(name);word=path.stem
            if path.parent.name!='data' or path.suffix!='.json' or word not in allowed:continue
            medians=json.loads(glyphs.read(name)).get('medians',[])
            strokes=[]
            for median in medians:
                stroke=E.Element('stroke')
                for x,y in median:E.SubElement(stroke,'point',x=str(round(x*1000/1024)),y=str(round((900-y)*1000/1024)))
                strokes.append(stroke)
            pixels=raster(strokes)
            if pixels and 0<len(strokes)<=48:
                records.append(word.encode().ljust(16,b'\0')+struct.pack('<HH',len(strokes),len(pixels))+struct.pack('<'+'H'*len(pixels),*pixels))
    pathlib.Path(output).write_bytes(b'HKS1'+struct.pack('<I',len(records))+b''.join(records))
    print('Shape templates:',len(records))
if __name__=='__main__':
    import sys
    z=zipfile.ZipFile(sys.argv[1]);build(z.read(next(n for n in z.namelist() if n.endswith('/handwriting-zh_TW.xml'))),sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
