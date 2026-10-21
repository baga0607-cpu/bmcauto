# -*- coding: utf-8 -*-
"""
Report Generator Module v2.0
嚴格遵循官方 QA 測試報告格式 (FWA-AIS6172 BMC Test Report) 的 PDF 產出引擎。

特點：
1. 乾淨官方排版：封面 / 目錄 / DUT 環境配置表 / 各 Test Case 詳細步驟與驗證摘要。
2. 方案 A 內嵌附件 (PDF Embedded File Attachments)：
   - 每個 Test Case 的完整 Test log 檔案直接嵌入 PDF 中。
   - 頁面內顯示可點選的 📎 連結（讓使用者知道附件在哪裡並如何打開）。
   - 使用 pypdf 的 add_attachment()，在 Adobe Reader 左側「附件」面板可見。
3. 預留多元測試類型欄位 (Redfish API, BMC Web UI, IPMITool CLI)。
4. 未具備欄位預留 Placeholder，等待將來開發填入。
"""

from case_log import test_log_text
import os
import json
import sys
import sqlite3.dbapi2 as sqlite3
import datetime
import glob
import io
import re
import unicodedata

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pypdf


# ── 字型設定：嘗試註冊支援 CJK 中文的字型 ────────────────────────────────────
# 優先使用 Microsoft YaHei（支援繁/簡中文+英文），回退至系統 Helvetica
_CJK_FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyh.ttc',      # Microsoft YaHei (主要)
    r'C:\Windows\Fonts\msjh.ttc',      # Microsoft JhengHei
    r'C:\Windows\Fonts\simsun.ttc',    # SimSun
]
_CJK_FONT_NAME  = 'Helvetica'    # 預設值，若成功載入則覆蓋
_CJK_FONT_BOLD  = 'Helvetica-Bold'
_CJK_FONT_ITALIC = 'Helvetica-Oblique'

for _candidate in _CJK_FONT_CANDIDATES:
    if os.path.exists(_candidate):
        try:
            pdfmetrics.registerFont(TTFont('CJKFont',  _candidate, subfontIndex=0))
            pdfmetrics.registerFont(TTFont('CJKFontB', _candidate, subfontIndex=0))
            _CJK_FONT_NAME  = 'CJKFont'
            _CJK_FONT_BOLD  = 'CJKFontB'
            _CJK_FONT_ITALIC = 'CJKFont'   # TTC 通常無獨立斜體
            print(f'[Font] Loaded CJK font from: {_candidate}')
            break
        except Exception as _e:
            print(f'[Font] Failed to load {_candidate}: {_e}')


# ── 常數 ────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PAGE_W, PAGE_H = A4
MARGIN        = 35
COL_W         = PAGE_W - 2 * MARGIN

# 色系 (對照官方 PDF 藍黑色標題、灰白表格)
C_NAVY        = colors.HexColor('#1A3A5C')   # 深藍標題
C_BLUE_HEADER = colors.HexColor('#2E5D9E')   # 藍色表格標題列
C_LIGHT_BLUE  = colors.HexColor('#D6E4F0')   # 淡藍交替列
C_WHITE       = colors.white
C_DARK_TEXT   = colors.HexColor('#1C1C1C')
C_MUTED       = colors.HexColor('#6C757D')
C_GREEN       = colors.HexColor('#1E7E34')
C_RED         = colors.HexColor('#B71C1C')
C_YELLOW      = colors.HexColor('#856404')
C_BORDER      = colors.HexColor('#BDC3C7')
C_ROW_ALT     = colors.HexColor('#F4F8FC')   # 淡藍交替


# ── 自訂 Canvas (頁首 / 頁尾 / 頁碼) ────────────────────────────────────────
class NumberedCanvas(rl_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._report_meta = {}   # External injection: {task_name, generated_at}

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_chrome(num_pages)
            super().showPage()
        super().save()

    def _draw_page_chrome(self, total_pages):
        self.saveState()
        pg = self._pageNumber

        if pg == 1:
            self.restoreState()
            return

        # ─ 頁首 ─
        self.setFont('Helvetica-Bold', 8)
        self.setFillColor(C_NAVY)
        task_name = self._report_meta.get('task_name', '')
        self.drawString(MARGIN, PAGE_H - 22, f'BMC Automated Test Report  |  {task_name}')
        self.setFillColor(C_MUTED)
        self.setFont('Helvetica', 8)
        self.drawRightString(PAGE_W - MARGIN, PAGE_H - 22,
                             self._report_meta.get('generated_at', ''))
        self.setStrokeColor(C_BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN, PAGE_H - 26, PAGE_W - MARGIN, PAGE_H - 26)

        # ─ 頁尾 ─
        self.line(MARGIN, 30, PAGE_W - MARGIN, 30)
        self.setFont('Helvetica', 8)
        self.setFillColor(C_MUTED)
        self.drawString(MARGIN, 18, 'CONFIDENTIAL — For Internal QA Use Only')
        self.drawRightString(PAGE_W - MARGIN, 18, f'Page {pg} of {total_pages}')

        self.restoreState()


# ── 樣式定義 ─────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()

    def S(name, **kw):
        kw.setdefault('parent', base['Normal'])
        return ParagraphStyle(name, **kw)

    return {
        'cover_title': S('CoverTitle',
            fontName=_CJK_FONT_BOLD, fontSize=28, leading=36,
            textColor=C_NAVY, alignment=1, spaceAfter=8),
        'cover_sub': S('CoverSub',
            fontName=_CJK_FONT_NAME, fontSize=14, leading=20,
            textColor=C_MUTED, alignment=1, spaceAfter=6),
        'cover_ver': S('CoverVer',
            fontName=_CJK_FONT_BOLD, fontSize=12, leading=18,
            textColor=C_DARK_TEXT, alignment=1),
        'section_title': S('SectionTitle',
            fontName=_CJK_FONT_BOLD, fontSize=15, leading=20,
            textColor=C_NAVY, spaceBefore=14, spaceAfter=6),
        'tc_title': S('TcTitle',
            fontName=_CJK_FONT_BOLD, fontSize=12, leading=16,
            textColor=C_NAVY, spaceBefore=10, spaceAfter=4),
        'tbl_hdr': S('TblHdr',
            fontName=_CJK_FONT_BOLD, fontSize=9, leading=12,
            textColor=C_WHITE),
        'tbl_cell': S('TblCell',
            fontName=_CJK_FONT_NAME, fontSize=8.5, leading=13,
            textColor=C_DARK_TEXT),
        'tbl_cell_bold': S('TblCellBold',
            fontName=_CJK_FONT_BOLD, fontSize=8.5, leading=13,
            textColor=C_DARK_TEXT),
        'status_pass': S('StPass',
            fontName=_CJK_FONT_BOLD, fontSize=9, leading=13,
            textColor=C_GREEN),
        'status_fail': S('StFail',
            fontName=_CJK_FONT_BOLD, fontSize=9, leading=13,
            textColor=C_RED),
        'status_tbd': S('StTbd',
            fontName=_CJK_FONT_BOLD, fontSize=9, leading=13,
            textColor=C_YELLOW),
        'note': S('Note',
            fontName=_CJK_FONT_ITALIC, fontSize=8, leading=12,
            textColor=C_MUTED),
        'body': S('Body',
            fontName=_CJK_FONT_NAME, fontSize=9, leading=14,
            textColor=C_DARK_TEXT),
        'toc_cat': S('TocCat',
            fontName=_CJK_FONT_BOLD, fontSize=10, leading=14,
            textColor=C_NAVY, spaceBefore=4),
        'toc_tc': S('TocTc',
            fontName=_CJK_FONT_NAME, fontSize=9, leading=13,
            textColor=C_DARK_TEXT, leftIndent=16),
        'attach_hint': S('AttachHint',
            fontName=_CJK_FONT_BOLD, fontSize=8, leading=12,
            textColor=colors.HexColor('#2E5D9E')),
        'attach_item': S('AttachItem',
            fontName=_CJK_FONT_NAME, fontSize=8, leading=12,
            textColor=colors.HexColor('#2E5D9E')),
    }


# ── 工具函數 ─────────────────────────────────────────────────────────────────
def _safe_name(name):
    return re.sub(r'[^\w\-]', '_', name).strip('_') or 'TC'


def _status_para(status, styles):
    s = (status or 'tbd').lower()
    if s in ('passed', 'pass'):
        return Paragraph('PASSED  [OK]', styles['status_pass'])
    elif s in ('failed', 'fail'):
        return Paragraph('FAILED  [NG]', styles['status_fail'])
    elif s in ('block', 'blocked'):
        return Paragraph('BLOCK', styles['status_tbd'])
    else:
        return Paragraph('TBD', styles['status_tbd'])


def _cfg_table(rows, styles):
    """建立設定參數表 (2 欄)"""
    data = [[Paragraph('<b>Parameter</b>', styles['tbl_hdr']),
             Paragraph('<b>Value</b>', styles['tbl_hdr'])]]
    for k, v in rows:
        data.append([
            Paragraph(str(k), styles['tbl_cell_bold']),
            Paragraph(str(v) if v else '<i style="color:#888">N/A — Reserved for future configuration</i>', styles['tbl_cell']),
        ])
    t = Table(data, colWidths=[COL_W * 0.35, COL_W * 0.65])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ('GRID', (0, 0), (-1, -1), 0.4, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _sanitize_for_pdf(text):
    """清除 PDF/ReportLab 無法渲染的字元：emoji、控制字元、XML 特殊字元"""
    # 跳脫 XML/HTML 特殊字元
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 移除 emoji 與不可見控制字元 (保留中文、英文、標點、ASCII 可見字元)
    clean = []
    for ch in text:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        # 保留：Basic ASCII 可見字元 / CJK 字元範圍 / 常見標點
        if (0x20 <= cp <= 0x7E) or (0x4E00 <= cp <= 0x9FFF) or \
           (0x3000 <= cp <= 0x303F) or (0xFF00 <= cp <= 0xFFEF) or \
           cat in ('Ll', 'Lu', 'Lt', 'Lo', 'Nd', 'Zs'):
            clean.append(ch)
        elif ch in ('\n', '\r', '\t'):
            clean.append(' ')
        # 其他 emoji / 特殊符號 → 略過
    return ''.join(clean)


def _parse_log_summary(log_path, max_lines=10):
    """從 result log 中萃取關鍵執行摘要（移除雜訊行 + 安全化輸出）"""
    if not os.path.exists(log_path):
        return 'No execution log found.'
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        clean = []
        for ln in lines:
            ln = ln.strip()
            if not ln or ln.startswith('===') or ln.startswith('---'):
                continue
            # 移除時間戳前綴
            ln = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ - \w+ - ', '', ln)
            ln = _sanitize_for_pdf(ln)
            if ln.strip():
                clean.append(ln.strip())
        summary_lines = clean[-max_lines:] if len(clean) > max_lines else clean
        return '<br/>'.join(summary_lines) if summary_lines else 'Execution completed.'
    except Exception as e:
        return f'Error reading log: {e}'


def _determine_test_type(script_path):
    """根據 script_path 推斷測試類型"""
    if not script_path:
        return 'Redfish REST API'
    sp = (script_path or '').lower()
    if 'ipmi' in sp or 'ipmitool' in sp:
        return 'IPMITool CLI'
    elif 'web' in sp or 'browser' in sp or 'selenium' in sp:
        return 'BMC Web UI'
    return 'Redfish REST API'


# ── 主函數 ───────────────────────────────────────────────────────────────────
def generate_task_pdf_report(task_id, output_path, db_path=None, log_dir=None):
    """
    Generate the official PDF report for a Task and embed API / Console Logs.
    """
    if db_path is None:
        db_path = os.path.join(BASE_DIR, 'workspace', 'testcase_meta.db')
    if log_dir is None:
        log_dir = os.path.join(BASE_DIR, 'workspace', 'logs')

    if not os.path.exists(db_path):
        raise FileNotFoundError(f'Database file not found: {db_path}')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    task_table = 'tasks'
    task_tc_table = 'task_testcases'
    task_fk_col = 'task_id'

    # Query Task basic data.
    task = cur.execute(f'SELECT * FROM {task_table} WHERE id = ?', (task_id,)).fetchone()
    if not task:
        conn.close()
        raise ValueError(f'Task ID not found: {task_id}')

    task_name = task['name'] or 'Unnamed_Task'
    env_config = task['environment_config'] or ''
    task_metadata = json.loads(task['task_metadata'] or '{}')

    # ─ 查詢關聯 Test Cases ─
    rows = cur.execute(f"""
        SELECT btc.testcase_id, btc.position, btc.status, btc.bug_id, btc.executed_at, btc.result_json, btc.log_text, btc.api_log_text, btc.manual_override_json, btc.needs_retest,
               tc.display_name, tc.script_path,
               CASE WHEN parent.id IS NULL THEN folder.name ELSE parent.name || '/' || folder.name END AS category_name
        FROM {task_tc_table} btc
        JOIN testcases tc ON btc.testcase_id = tc.system_id
        LEFT JOIN plan_folders folder ON tc.folder_id = folder.id
        LEFT JOIN plan_folders parent ON folder.parent_id = parent.id
        WHERE btc.{task_fk_col} = ? AND tc.plan_id = (SELECT plan_id FROM tasks WHERE id = btc.task_id)
        ORDER BY btc.position ASC
    """, (task_id,)).fetchall()

    # Query Plan name from the Task table.
    plan_row = cur.execute(f"""
        SELECT pp.name, p.name as proj_name
        FROM {task_table} t
        JOIN project_plans pp ON t.plan_id = pp.id
        JOIN projects p ON pp.project_id = p.id
        WHERE t.id = ?
    """, (task_id,)).fetchone()
    plan_name = plan_row['name'] if plan_row else 'N/A'
    proj_name = plan_row['proj_name'] if plan_row else 'N/A'
    conn.close()

    # ─ 依類別分組 ─
    categories_map = {}
    for r in rows:
        cat = r['category_name'] or 'General Test Cases'
        categories_map.setdefault(cat, []).append(r)

    now_str  = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_str = datetime.datetime.now().strftime('%Y/%m/%d')

    styles = _build_styles()
    story  = []

    # ════════════════════════════════════════════════════════════════════════
    # 1. COVER PAGE
    # ════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 60))
    story.append(Paragraph('BMC Test Report', styles['cover_title']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f'Project : {proj_name}', styles['cover_sub']))
    story.append(Paragraph(f'Plan : {plan_name}', styles['cover_sub']))
    story.append(Paragraph(f'Task : {task_name}', styles['cover_sub']))
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width=COL_W, thickness=2, color=C_NAVY))
    story.append(Spacer(1, 20))

    # 封面統計概覽
    total   = len(rows)
    passed  = sum(1 for r in rows if (r['status'] or '').lower() in ('passed', 'pass'))
    failed  = sum(1 for r in rows if (r['status'] or '').lower() in ('failed', 'fail'))
    blocked = sum(1 for r in rows if (r['status'] or '').lower() in ('block', 'blocked'))
    tbd     = total - passed - failed - blocked

    cover_stats = [
        [Paragraph('<b>Total Cases</b>', styles['tbl_hdr']),
         Paragraph('<b>Passed</b>', styles['tbl_hdr']),
         Paragraph('<b>Failed</b>', styles['tbl_hdr']),
         Paragraph('<b>Block</b>', styles['tbl_hdr']),
         Paragraph('<b>TBD</b>', styles['tbl_hdr'])],
        [Paragraph(str(total), styles['tbl_cell_bold']),
         Paragraph(f'<font color="#1E7E34"><b>{passed}</b></font>', styles['tbl_cell']),
         Paragraph(f'<font color="#B71C1C"><b>{failed}</b></font>', styles['tbl_cell']),
         Paragraph(str(blocked), styles['tbl_cell']),
         Paragraph(str(tbd), styles['tbl_cell'])],
    ]
    t_stats = Table(cover_stats, colWidths=[COL_W / 5] * 5)
    t_stats.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
        ('BACKGROUND', (0, 1), (-1, 1), C_ROW_ALT),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 40))

    # 簽核批准表 (對照官方 PDF)
    approval_data = [
        [Paragraph('<b>Prepared By</b>', styles['tbl_hdr']),
         Paragraph('<b>Reviewed By (NSP)</b>', styles['tbl_hdr']),
         Paragraph('<b>Approved By (DQA)</b>', styles['tbl_hdr']),
         Paragraph('<b>Issue Date</b>', styles['tbl_hdr'])],
        [Paragraph('Automated Agent', styles['tbl_cell']),
         Paragraph('— Reserved —', styles['tbl_cell']),
         Paragraph('— Reserved —', styles['tbl_cell']),
         Paragraph(date_str, styles['tbl_cell'])],
        [Paragraph('Version : 1.0', styles['note']), '', '', ''],
    ]
    t_appr = Table(approval_data, colWidths=[COL_W / 4] * 4)
    t_appr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_NAVY),
        ('GRID', (0, 0), (-1, 1), 0.5, C_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('SPAN', (0, 2), (-1, 2)),
    ]))
    story.append(t_appr)
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # 2. TABLE OF CONTENTS
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph('Table Of Contents', styles['section_title']))
    story.append(HRFlowable(width=COL_W, thickness=1, color=C_BORDER))
    story.append(Spacer(1, 10))

    story.append(Paragraph('00.00.00 &nbsp; DUT Environment & Configuration', styles['toc_cat']))
    for idx, (cat_name, cat_rows) in enumerate(categories_map.items(), 1):
        story.append(Paragraph(
            f'0{idx}.00.00 &nbsp; {cat_name} &nbsp;&nbsp;'
            f'<font color="#888888">({len(cat_rows)} test cases)</font>',
            styles['toc_cat']))
        for r in cat_rows:
            tc_nm  = r['display_name'] or r['testcase_id']
            status = (r['status'] or 'tbd').upper()
            color  = '#1E7E34' if status == 'PASSED' else ('#B71C1C' if status == 'FAILED' else '#856404')
            story.append(Paragraph(
                f'• {tc_nm} &nbsp;'
                f'<font color="{color}"><b>[{status}]</b></font>',
                styles['toc_tc']))

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # 3. DUT ENVIRONMENT & CONFIGURATION (00.00.00)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph('Test Suite : 00.00.00 DUT Environment & Configuration',
                           styles['section_title']))
    story.append(HRFlowable(width=COL_W, thickness=1, color=C_BORDER))
    story.append(Spacer(1, 8))

    # 基本欄位 (完整對照官方 PDF Test Configuration Table)
    cfg_rows = [
        ('Project Name',            proj_name),
        ('Test Plan',               plan_name),
        ('Task Name',         task_name),
        ('Report Version',          '1.0'),
        ('Test Date',               now_str),
        ('Environment / DUT Note',  env_config or None),
        # ── DUT Hardware (預留) ──────────────────────────────
        ('DUT Model / Platform',    None),   # 預留：將來從 config.yaml 或 env_config 填入
        ('DUT Serial Number',       None),
        ('BMC Firmware Version',    None),
        ('BIOS Version',            None),
        ('Firmware / Task Label',   None),
        # ── Test Environment (預留) ─────────────────────────
        ('OS Version (Host)',       None),
        ('IPMITool Version',        None),
        ('Test Site',               None),
        ('Tester / Engineer',       None),
        ('Test Environment Photo',  None),   # 預留：圖檔名或連結
        # ── 已知資訊 ────────────────────────────────────────
        ('Test Engine',             'BMC Automation Suite v3.0'),
        ('Supported Test Types',    'Redfish REST API  |  BMC Web UI  |  IPMITool CLI'),
        ('Requirements / Keywords', None),
        ('Issue ID',                None),
    ]
    cfg_rows.extend((str(key).replace('_', ' ').title(), str(value)) for key, value in task_metadata.items())
    story.append(_cfg_table(cfg_rows, styles))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # 4. DETAILED TEST CASE REPORTS (每個 Category 一大節)
    # ════════════════════════════════════════════════════════════════════════
    attachments_to_add = []   # [(display_fname, abs_path)]

    for cat_idx, (cat_name, cat_rows) in enumerate(categories_map.items(), 1):
        story.append(Paragraph(
            f'Test Suite : 0{cat_idx}.00.00 {cat_name}',
            styles['section_title']))
        story.append(HRFlowable(width=COL_W, thickness=1, color=C_BORDER))
        story.append(Spacer(1, 6))

        for tc_idx, r in enumerate(cat_rows, 1):
            tc_id    = r['testcase_id']
            tc_name  = r['display_name'] or tc_id
            status   = r['status'] or 'tbd'
            exec_at  = r['executed_at'] or 'N/A'
            bug_id   = r['bug_id'] or 'None'
            tc_type  = _determine_test_type(r['script_path'])
            safe_nm  = _safe_name(tc_name)

            from xml.sax.saxutils import escape
            result_details = r['result_json'] or ''
            try:
                result_data = json.loads(result_details) if result_details else {}
            except (ValueError, TypeError):
                result_data = {}
            if not isinstance(result_data, dict):
                result_data = {}
            log_excerpt = r['log_text'] or 'No latest execution log.'
            if isinstance(result_data.get('log_records'), list):
                # Table rows cannot split arbitrarily long evidence across pages.
                records = [entry for entry in result_data['log_records'] if isinstance(entry, dict)]
                final = next((entry for entry in reversed(records) if entry.get('kind') == 'finish'), {})
                checks = [entry for entry in records if entry.get('kind') == 'check']
                reason = str(final.get('reason', ''))
                reason = reason[:300] + ('…' if len(reason) > 300 else '')
                result_details = (f"Result: {final.get('status', status)}\nReason: {reason}\n"
                                  f"Checks: {sum(bool(entry.get('passed')) for entry in checks)}/{len(checks)} passed")
                log_excerpt = 'Full execution and HTTP evidence are included in the log attachments.'
            exec_notes = escape(result_details + ('\n' if result_details else '') + log_excerpt).replace('\n', '<br/>')
            if r['needs_retest']:
                exec_notes = '<b>Plan definition or Task connection settings changed. Rerun needed; retained evidence predates the current settings.</b><br/><br/>' + exec_notes
            manual = json.loads(r['manual_override_json']) if r['manual_override_json'] else None
            if manual:
                manual_note = ('Manual status: ' + manual['status'] + '\nModified at: ' + manual['modified_at']
                               + '\nReason: ' + (manual['reason'] or 'Not provided'))
                exec_notes = escape(manual_note).replace('\n', '<br/>') + '<br/><br/>' + exec_notes
            attach_names = []
            for content in [test_log_text(r['log_text'], r['api_log_text'])]:
                if content:
                    name = f'test_{tc_id}.log'
                    files = result_data.get('log_files', {})
                    candidate = files.get('test') if isinstance(files, dict) else None
                    if not candidate and isinstance(files, dict):
                        candidate = files.get('execution') or files.get('api')
                        if isinstance(candidate, str):
                            candidate = candidate.removesuffix('__result.log').removesuffix('__http.log') + '__test.log'
                    if (isinstance(candidate, str) and candidate.endswith('.log') and len(candidate) <= 150
                            and not any(c in candidate for c in '<>:\"/\\|?*')
                            and not any(ord(c) < 32 for c in candidate)):
                        name = candidate
                    attachments_to_add.append((name, content.encode('utf-8')))
                    attach_names.append(name)

            # ── Test Case 標題 ──
            tc_header_text = (
                f'<b>Test Case {cat_idx}.{tc_idx:02d} : {tc_name}</b>'
                f' &nbsp;[Version : 1]'
                f' &nbsp;[Type : {tc_type}]'
            )
            story.append(Paragraph(tc_header_text, styles['tc_title']))

            # ── Step 明細表 ──
            # 欄位嚴格對照官方 PDF: #, Step actions, Expected Results,
            #                        Execution notes, Exec Status
            step_hdr = [
                Paragraph('#', styles['tbl_hdr']),
                Paragraph('Step actions', styles['tbl_hdr']),
                Paragraph('Expected Results', styles['tbl_hdr']),
                Paragraph('Execution notes', styles['tbl_hdr']),
                Paragraph('Execution<br/>Status', styles['tbl_hdr']),
            ]

            # Step actions 文字 (從 script_path 推導)
            step_action = (
                f'Execute the Plan Test Case:<br/>'
                f'<b>{tc_name}</b><br/><br/>'
                f'<font color="#6C757D">Module path:<br/>'
                f'{r["script_path"] or "Automated sequence"}</font>'
            )

            # Expected Results (依測試類型給出通用期待)
            if tc_type == 'Redfish REST API':
                expected = (
                    'HTTP response code shall be 200 OK (or appropriate 2xx).<br/>'
                    'Response JSON schema must match Redfish specification.<br/>'
                    'No timeout or connection error shall occur.'
                )
            elif tc_type == 'IPMITool CLI':
                expected = (
                    'IPMI command shall return exit code 0.<br/>'
                    'Output data shall match expected format.<br/>'
                    'No error or warning message in stdout.'
                )
            else:
                expected = (
                    'Web UI page shall load within acceptable time.<br/>'
                    'UI elements shall respond correctly to interaction.<br/>'
                    'No JavaScript console error or page crash.'
                )

            # 附件提示行 (讓使用者知道可以打開附件)
            if attach_names:
                attach_hint = (
                    '<br/><br/><font color="#2E5D9E"><b>'
                    '[ATTACH] Full logs are embedded in this PDF as file attachments.<br/>'
                    'Open the "Attachments" panel in Adobe Acrobat / Reader to view:<br/>'
                    '</b></font>' +
                    ''.join([f'<font color="#2E5D9E">  - {escape(n)}</font><br/>' for n in attach_names])
                )
            else:
                attach_hint = '<br/><font color="#856404"><i>No log files found for this test case.</i></font>'

            exec_notes_cell = exec_notes + attach_hint


            step_row = [
                Paragraph('1', styles['tbl_cell']),
                Paragraph(step_action, styles['tbl_cell']),
                Paragraph(expected, styles['tbl_cell']),
                Paragraph(exec_notes_cell, styles['tbl_cell']),
                _status_para(status, styles),
            ]

            step_table_data = [step_hdr, step_row]
            t_steps = Table(
                step_table_data,
                colWidths=[COL_W * w for w in [0.04, 0.20, 0.22, 0.38, 0.10, 0.06]])
            # 重新算一下比例 (5 欄)
            t_steps = Table(
                step_table_data,
                colWidths=[
                    COL_W * 0.04,   # #
                    COL_W * 0.21,   # Step actions
                    COL_W * 0.22,   # Expected Results
                    COL_W * 0.40,   # Execution notes
                    COL_W * 0.13,   # Status
                ])
            t_steps.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE]),
                ('GRID', (0, 0), (-1, -1), 0.4, C_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))

            # ── Execution Details 小表格 ──
            detail_data = [
                [Paragraph('<b>Test Case ID</b>', styles['tbl_cell_bold']),
                 Paragraph(tc_id, styles['tbl_cell']),
                 Paragraph('<b>Test Type</b>', styles['tbl_cell_bold']),
                 Paragraph(tc_type, styles['tbl_cell'])],
                [Paragraph('<b>Executed At</b>', styles['tbl_cell_bold']),
                 Paragraph(exec_at, styles['tbl_cell']),
                 Paragraph('<b>Execution Mode</b>', styles['tbl_cell_bold']),
                 Paragraph('Automated', styles['tbl_cell'])],
                [Paragraph('<b>Bug / Issue ID</b>', styles['tbl_cell_bold']),
                 Paragraph(bug_id, styles['tbl_cell']),
                 Paragraph('<b>Result Status</b>', styles['tbl_cell_bold']),
                 _status_para(status, styles)],
                [Paragraph('<b>Tester</b>', styles['tbl_cell_bold']),
                 Paragraph('N/A — Reserved for future configuration', styles['note']),
                 Paragraph('<b>Test Duration</b>', styles['tbl_cell_bold']),
                 Paragraph('N/A — Reserved for future configuration', styles['note'])],
            ]
            t_detail = Table(detail_data, colWidths=[
                COL_W * 0.18, COL_W * 0.32, COL_W * 0.18, COL_W * 0.32])
            t_detail.setStyle(TableStyle([
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [C_ROW_ALT, C_WHITE]),
                ('GRID', (0, 0), (-1, -1), 0.4, C_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))

            block = KeepTogether([
                t_steps,
                Spacer(1, 4),
                t_detail,
                Spacer(1, 16),
            ])
            story.append(block)

        story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # 5. RENDER PDF TO MEMORY (ReportLab)
    # ════════════════════════════════════════════════════════════════════════
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 10,
        bottomMargin=MARGIN + 10,
        title=f'BMC Test Report – {task_name}',
        author='BMC Automation Suite v3.0',
        subject='Automated QA Test Report',
    )

    # 注入報告 meta 到自訂 Canvas
    def canvas_factory(*args, **kwargs):
        c = NumberedCanvas(*args, **kwargs)
        c._report_meta = {'task_name': task_name, 'generated_at': now_str}
        return c

    doc.build(story, canvasmaker=canvas_factory)
    buf.seek(0)

    # ════════════════════════════════════════════════════════════════════════
    # 6. EMBED LOG FILES AS PDF ATTACHMENTS (pypdf)
    # ════════════════════════════════════════════════════════════════════════
    reader = pypdf.PdfReader(buf)
    writer = pypdf.PdfWriter()
    writer.append_pages_from_reader(reader)

    seen = set()
    embedded_count = 0
    for fname, fpath in attachments_to_add:
        if fname in seen:
            continue
        seen.add(fname)
        try:
            writer.add_attachment(fname, fpath)
            embedded_count += 1
            print(f'  [Attachment] Embedded: {fname}')
        except Exception as e:
            print(f'  [Warning] Unable to embed attachment {fname}: {e}')

    print(f'[Report] Total embedded attachments: {embedded_count}')

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'wb') as out_f:
        writer.write(out_f)

    print(f'[Report] PDF saved: {output_path}')
    return output_path


# ── CLI Entry Point ────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python report_generator.py <task_id>')
        sys.exit(1)
    task_arg = sys.argv[1]
    out = os.path.join(BASE_DIR, 'workspace', 'results', f'report_{task_arg}.pdf')
    try:
        print(f'Generating report for Task: {task_arg}')
        path = generate_task_pdf_report(task_arg, out)
        print(f'Done: {path}')
    except Exception as ex:
        print(f'Error: {ex}')
        sys.exit(1)
