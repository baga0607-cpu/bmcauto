"""Embed the installed Bahnschrift semibold instance in PDF case headings."""
import io
import os
from functools import lru_cache
from xml.sax.saxutils import escape

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


@lru_cache(maxsize=1)
def case_font():
    path = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'bahnschrift.ttf')
    if not os.path.isfile(path):
        return None
    try:
        from fontTools.ttLib import TTFont as SourceFont
        from fontTools.varLib.instancer import instantiateVariableFont
        source = SourceFont(path)
        if 'fvar' in source:
            source = instantiateVariableFont(source, {'wght': 600}, inplace=True)
        buffer = io.BytesIO()
        source.save(buffer)
        source.close()
        buffer.seek(0)
        pdfmetrics.registerFont(TTFont('ReportBahnschrift600', buffer))
        return 'ReportBahnschrift600'
    except (ImportError, OSError, ValueError):
        return None


def case_title_markup(text, fallback):
    font = case_font()
    if font is None:
        return escape(str(text))
    supported = pdfmetrics.getFont(font).face.charToGlyph
    chunks, run, current = [], '', None
    for char in str(text):
        selected = font if ord(char) in supported else fallback
        if current is not None and selected != current:
            chunks.append(f'<font name="{current}">{escape(run)}</font>')
            run = ''
        current = selected
        run += char
    if run:
        chunks.append(f'<font name="{current}">{escape(run)}</font>')
    return ''.join(chunks)
