"""SQL-backed files and bounded, inert previews. Never fetch external relationships."""
import base64
import io
import posixpath
import zipfile
import warnings
from pathlib import PurePosixPath
from html import escape
from defusedxml import ElementTree as ET
from PIL import Image
from pypdf import PdfReader
import olefile
from flask import Blueprint,request,g,jsonify,send_file
from .auth import protected
from .errors import require,AppError
from .schema import string,integer
from .service import own_order

bp=Blueprint('documents',__name__,url_prefix='/api/documents')
MAX_FILE=20*1024*1024
MIMES={'.pdf':'application/pdf','.txt':'text/plain','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
 '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation',
 '.doc':'application/msword','.xls':'application/vnd.ms-excel','.ppt':'application/vnd.ms-powerpoint',
 '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.bmp':'image/bmp'}
CATEGORIES={'contract','invoice','waybill','photo','report','other'}
META='DocumentID,Title,OriginalName,MediaType,Category,OrderID,OwnerUserID,FileSize,CreatedAt'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
Image.MAX_IMAGE_PIXELS=25_000_000


def filename(name):
    result=str(name or '').replace('\\','/').split('/')[-1]
    require(result not in ('','.','..') and len(result)<=255 and not any(ord(c)<32 or ord(c)==127 for c in result),'file_name')
    return result


def txt(raw):
    try:
        value=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        require('\x00' not in value,'file_invalid')
        return value
    except UnicodeError: raise AppError('txt_encoding') from None


def raster(raw):
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as im:
            kind=im.format
            require(im.width*im.height<=25_000_000,'file_complex')
            im.verify()
            return Image.MIME.get(kind)


def office(raw,ext):
    archive=zipfile.ZipFile(io.BytesIO(raw))
    try:
        infos=archive.infolist(); names=[x.filename for x in infos]
        require(len(infos)<=1500 and len(names)==len(set(names)) and sum(x.file_size for x in infos)<=40*1024*1024,'file_complex')
        main={'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}[ext]
        require(main in names and '[Content_Types].xml' in names,'file_invalid')
        for entry in infos:
            low=entry.filename.lower()
            require(not entry.flag_bits&1 and entry.file_size<=MAX_FILE and not low.startswith('/') and '..' not in PurePosixPath(low).parts,'file_invalid')
            require(not any(x in low for x in ('vbaproject','macrosheet','embeddings/','activex/','customui/')),'file_active')
            if low.endswith(('.xml','.rels')):
                raw_xml=archive.read(entry)
                require(b'macroenabled' not in raw_xml.lower(),'file_active')
                ET.fromstring(raw_xml)  # forbids entities/DTDs; relationships remain inert
        return archive
    except Exception:
        archive.close()
        raise


def validate_file(name,raw):
    require(0<len(raw)<=MAX_FILE,'file_size',413)
    ext=PurePosixPath(name).suffix.lower(); require(ext in MIMES,'file_type',415)
    try:
        if ext=='.txt': txt(raw)
        elif ext in ('.docx','.xlsx','.pptx'):
            with office(raw,ext): pass
        elif ext in ('.doc','.xls','.ppt'):
            require(olefile.isOleFile(io.BytesIO(raw)),'file_invalid')
            with olefile.OleFileIO(io.BytesIO(raw)) as ole:
                streams=ole.listdir(); names=['/'.join(x).lower() for x in streams]
                require(not any(any(w in n for w in ('vba','macros','objectpool','_xmlsignatures')) for n in names),'file_active')
                expected={'.doc':('worddocument',),'.xls':('workbook','book'),'.ppt':('powerpoint document',)}[ext]
                require(any(n in names for n in expected),'file_invalid')
                if ext=='.xls':
                    data=ole.openstream(next(n for n in expected if n in names)).read()
                    # BIFF BOF substream type 0x0040 denotes an Excel 4 macro sheet.
                    require(b'\x09\x08\x10\x00\x00\x06\x40\x00' not in data,'file_active')
        elif ext=='.pdf':
            require(raw.startswith(b'%PDF-'),'file_invalid')
            require(not any(k in raw for k in (b'/JavaScript',b'/JS',b'/Launch',b'/EmbeddedFile',b'/OpenAction',b'/RichMedia',b'/AcroForm')),'file_active')
            reader=PdfReader(io.BytesIO(raw),strict=True)
            require(not reader.is_encrypted and 1<=len(reader.pages)<=500,'file_complex')
            # Resolve encoded PDF names and indirect action dictionaries too.
            visited=set(); budget=[0]
            def inspect(obj):
                budget[0]+=1; require(budget[0]<=100000,'file_complex')
                if hasattr(obj,'idnum'):
                    identity=(obj.idnum,obj.generation)
                    if identity in visited:return
                    visited.add(identity);obj=obj.get_object()
                if isinstance(obj,dict):
                    require(not any(str(k) in {'/JS','/JavaScript','/AA','/OpenAction','/EmbeddedFiles','/RichMedia','/AcroForm','/XFA'} for k in obj),'file_active')
                    require(str(obj.get('/S','')) not in {'/JavaScript','/Launch','/GoToR','/SubmitForm','/ImportData'},'file_active')
                    for value in obj.values():inspect(value)
                elif isinstance(obj,(list,tuple)):
                    for value in obj:inspect(value)
            inspect(reader.trailer)
        else: require(raster(raw)==MIMES[ext],'file_invalid')
    except AppError: raise
    except Exception: raise AppError('file_invalid') from None
    return MIMES[ext]


def docx_preview(raw):
    with office(raw,'.docx') as archive:
        document=ET.fromstring(archive.read('word/document.xml'))
        body=document.find('w:body',NS); require(body is not None,'file_invalid')
        relationships={}
        if 'word/_rels/document.xml.rels' in archive.namelist():
            for rel in ET.fromstring(archive.read('word/_rels/document.xml.rels')):
                if rel.get('TargetMode')!='External':
                    relationships[rel.get('Id')]=posixpath.normpath('word/'+rel.get('Target',''))
        budget=[0,0]
        def paragraph(node):
            output=[]
            for child in node.iter():
                tag=child.tag.rsplit('}',1)[-1]
                if tag=='t': output.append(escape(child.text or ''))
                elif tag=='br': output.append('<br>')
                elif tag=='tab': output.append(' &emsp; ')
                elif tag=='blip':
                    target=relationships.get(child.get('{'+NS['r']+'}embed'),'')
                    if target.startswith('word/media/') and target in archive.namelist():
                        raw_image=archive.read(target); budget[1]+=len(raw_image)
                        require(budget[1]<=8*1024*1024,'preview_large')
                        mime=raster(raw_image)
                        require(mime in ('image/png','image/jpeg','image/gif','image/webp','image/bmp'),'file_invalid')
                        output.append('<img alt="" src="data:'+mime+';base64,'+base64.b64encode(raw_image).decode()+'">')
            result='<p>'+''.join(output)+'</p>'; budget[0]+=len(result)
            require(budget[0]<=12*1024*1024,'preview_large')
            return result
        html=[]
        for node in body:
            tag=node.tag.rsplit('}',1)[-1]
            if tag=='p': html.append(paragraph(node))
            elif tag=='tbl':
                html.append('<table>')
                for row in node.findall('w:tr',NS):
                    html.append('<tr>')
                    for cell in row.findall('w:tc',NS): html.append('<td>'+''.join(paragraph(p) for p in cell.findall('w:p',NS))+'</td>')
                    html.append('</tr>')
                html.append('</table>')
        return ''.join(html)


def visibility():
    if g.user['Role']=='admin': return '',()
    return ' WHERE (OwnerUserID=? OR OrderID IN (SELECT OrderID FROM dbo.Orders WHERE ClientID=?))',(g.user['UserID'],g.user['ClientID'])


def get_document(did,content=False):
    where,params=visibility()
    where+=(' AND ' if where else ' WHERE ')+'DocumentID=?'
    row=g.q.one('SELECT '+META+(',Content' if content else '')+' FROM dbo.Documents'+where,(*params,did))
    require(row,'not_found',404)
    return row


@bp.get('')
@protected()
def list_files():
    where,params=visibility(); values=list(params)
    for name in ('Category','OrderID'):
        if request.args.get(name):
            where+=(' AND ' if where else ' WHERE ')+name+'=?'; values.append(request.args[name])
    if request.args.get('search'):
        where+=(' AND ' if where else ' WHERE ')+'(Title LIKE ? OR OriginalName LIKE ?)'; values.extend(['%'+request.args['search'][:160]+'%']*2)
    return jsonify(rows=g.q.rows('SELECT '+META+' FROM dbo.Documents'+where+' ORDER BY DocumentID DESC',values))


@bp.post('')
@protected(write=True)
def upload():
    require('file' in request.files and len(request.files.getlist('file'))==1,'file_required')
    file=request.files['file']; name=filename(file.filename); raw=file.read(MAX_FILE+1); mime=validate_file(name,raw)
    title=string(request.form.get('Title') or name,160,'Title'); category=request.form.get('Category','other')
    require(category in CATEGORIES,'invalid',field='Category')
    oid=integer(request.form['OrderID']) if request.form.get('OrderID') else None
    if oid: own_order(g.q,g.user,oid)
    did=g.q.insert('Documents','DocumentID',dict(Title=title,OriginalName=name,MediaType=mime,Category=category,OrderID=oid,OwnerUserID=g.user['UserID'],FileSize=len(raw),Content=raw))
    return jsonify(id=did),201


@bp.delete('/<int:did>')
@protected(write=True)
def delete(did):
    row=get_document(did)
    require(g.user['Role']=='admin' or row['OwnerUserID']==g.user['UserID'],'forbidden',403)
    g.q.execute('DELETE dbo.Documents WHERE DocumentID=?',(did,))
    return jsonify(ok=True)


@bp.get('/<int:did>/file')
@protected()
def content(did):
    row=get_document(did,True)
    inline=request.args.get('inline')=='1' and (row['MediaType'].startswith('image/') or row['MediaType']=='application/pdf')
    return send_file(io.BytesIO(bytes(row['Content'])),mimetype=row['MediaType'],download_name=row['OriginalName'],as_attachment=not inline,max_age=0)


@bp.get('/<int:did>/preview')
@protected()
def preview(did):
    row=get_document(did,True); raw=bytes(row.pop('Content')); ext=PurePosixPath(row['OriginalName']).suffix.lower()
    html=''; kind='download'
    if ext=='.pdf': kind='pdf'
    elif row['MediaType'].startswith('image/'): kind='image'
    elif ext=='.txt':
        require(len(raw)<=2*1024*1024,'preview_large'); kind='text'; html='<pre>'+escape(txt(raw))+'</pre>'
    elif ext=='.docx': kind='docx'; html=docx_preview(raw)
    return jsonify(document=row,kind=kind,html=html)
