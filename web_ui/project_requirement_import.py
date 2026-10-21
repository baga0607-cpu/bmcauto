"""Read the product requirements XLSX format without executing workbook content."""
import io
import hashlib
import posixpath
import re
import zipfile
from collections import defaultdict, deque
from xml.etree import ElementTree as ET

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def parse_workbook(payload, filename):
    from project_information import blank_information, validate_document
    if not filename.lower().endswith('.xlsx') or len(payload) > 10_000_000:
        raise ValueError('Choose an .xlsx workbook no larger than 10 MB.')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries)>1000 or sum(e.file_size for e in entries)>50_000_000:
                raise ValueError('Workbook contents exceed the import limit.')
            if any('vbaproject' in e.filename.lower() for e in entries):
                raise ValueError('Macro-enabled workbooks are not supported.')
            def xml(path):
                raw=archive.read(path)
                if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                    raise ValueError('Unsupported workbook XML.')
                return ET.fromstring(raw)
            strings=[]
            if 'xl/sharedStrings.xml' in archive.namelist():
                strings=[''.join(n.itertext()) for n in xml('xl/sharedStrings.xml').findall('s:si',NS)]
            relationships={n.attrib['Id']:n.attrib.get('Target','') for n in xml('xl/_rels/workbook.xml.rels') if n.attrib.get('TargetMode')!='External'}
            sheets=[]
            for sheet in xml('xl/workbook.xml').findall('s:sheets/s:sheet',NS):
                rid=sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                target=relationships[rid]
                path=posixpath.normpath(posixpath.join('xl',target)) if not target.startswith('/') else target.lstrip('/')
                if not path.startswith('xl/'):
                    raise ValueError('Invalid worksheet location.')
                rows=[]
                for row in xml(path).findall('s:sheetData/s:row',NS):
                    values={}
                    for cell in row.findall('s:c',NS):
                        addr=cell.attrib['r'];col=re.sub(r'\d','',addr);kind=cell.attrib.get('t');value=cell.find('s:v',NS)
                        if cell.find('s:f',NS) is not None and (value is None or value.text is None):
                            raise ValueError('Recalculate and save the workbook in Excel before importing formulas.')
                        if kind=='e':raise ValueError('Resolve spreadsheet error cells before importing.')
                        text=value.text or '' if value is not None else ''
                        if kind=='s':text=strings[int(text)]
                        elif kind=='inlineStr':text=''.join(cell.find('s:is',NS).itertext())
                        values[col]=text
                    rows.append((row.attrib['r'],values))
                    if len(rows)>5000:raise ValueError('A worksheet exceeds 5000 rows.')
                sheets.append((sheet.attrib['name'],rows))
    except (zipfile.BadZipFile,KeyError,IndexError,ET.ParseError,TypeError) as exc:
        raise ValueError('The file is not a readable product requirements workbook.') from exc
    candidates=[(name,rows,index) for name,rows in sheets for index,(_,v) in enumerate(rows[:20]) if v.get('A','').strip()=='Category' and v.get('B','').strip()=='Item' and v.get('D','').strip()=='Target Specification']
    if len(candidates)!=1:raise ValueError('Expected one requirements sheet with Category, Item and Target Specification columns.')
    name,rows,header=candidates[0]
    doc=blank_information();doc['categories']=[]
    title=rows[0][1].get('A','');author=re.search(r'Author:\s*([^)]*)',title)
    doc['metadata'].update(product_name=name,document_title=title,author=author.group(1).strip() if author else '')
    doc['source'].update(filename=filename,requirement_sheet=name,sha256=hashlib.sha256(payload).hexdigest())
    category=None
    for number,v in rows[header+1:]:
        if v.get('A','').strip():
            category={'id':'category-'+number,'name':v['A'],'items':[]};doc['categories'].append(category)
        if not v.get('B','').strip():continue
        if category is None:raise ValueError('A requirement item has no category.')
        category['items'].append(dict(id='item-'+number,name=v['B'],guidance=v.get('C',''),target=v.get('D',''),remarks=v.get('E',''),heading=not any(v.get(c,'') for c in ['C','D','E']),source_ref=f'{name}!B{number}:E{number}',sku_values={}))
    comparisons=[(n,r) for n,r in sheets if re.sub(r'\s','',n).casefold() in ('sku比較','skucomparison')]
    if len(comparisons)>1:raise ValueError('Expected at most one SKU comparison sheet.')
    if comparisons:
        cname,crows=comparisons[0];doc['source']['comparison_sheet']=cname
        if not crows:raise ValueError('The SKU comparison sheet is empty.')
        headers=crows[0][1]
        columns=[c for c,v in headers.items() if c not in ('A','B','C') and v.strip() and v.strip().casefold() not in ('備註','remarks','remark','comment','notes')]
        doc['skus']=[{'id':c,'name':headers[c]} for c in columns]
        matching=defaultdict(deque)
        for cat in doc['categories']:
            for item in cat['items']:matching[(cat['name'].strip(),item['name'].strip())].append(item)
        current=''
        for number,v in crows[1:]:
            current=v.get('A','').strip() or current
            if not v.get('B','').strip():continue
            key=(current,v['B'].strip())
            if not matching[key]:raise ValueError(f'SKU comparison row {number} does not match a requirement item: {v["B"]}')
            item=matching[key].popleft();item['sku_values']={c:v.get(c,'') for c in columns}
            item['source_ref']+=f'; {cname}!{number}'
            for c,label in headers.items():
                if label.strip().casefold() in ('備註','remarks','remark','comment','notes') and v.get(c,'') and v[c]!=item['remarks']:
                    item['remarks']+=('\n' if item['remarks'] else '')+v[c]
    return name,validate_document(doc)
