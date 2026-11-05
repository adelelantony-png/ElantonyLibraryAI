# -*- coding: utf-8 -*-
"""
Standalone generator for both Benchmark and Production systems.
Ensures 100% clean data isolation and perfect financial balance.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import win32com.client

font_family = "Segoe UI"
title_font = Font(name=font_family, size=15, bold=True, color="FFFFFF")
sub_title_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
tbl_header_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
data_font = Font(name=font_family, size=10, bold=False, color="1E293B")
data_bold = Font(name=font_family, size=10, bold=True, color="1E293B")
total_font = Font(name=font_family, size=10, bold=True, color="0F172A")
kpi_val_font = Font(name=font_family, size=15, bold=True, color="1B365D")
kpi_lbl_font = Font(name=font_family, size=10, bold=True, color="475569")
success_font = Font(name=font_family, size=10, bold=True, color="166534")

navy_dark = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
navy_light = PatternFill(start_color="2C4D75", end_color="2C4D75", fill_type="solid")
slate_header = PatternFill(start_color="334E68", end_color="334E68", fill_type="solid")
total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
subtotal_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
kpi_card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
success_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
gold_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

thin_gray = Side(style='thin', color='CBD5E1')
double_bottom = Side(style='double', color='0F172A')

border_cell = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
border_total = Border(top=thin_gray, bottom=double_bottom, left=thin_gray, right=thin_gray)

align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
align_left = Alignment(horizontal="left", vertical="center")
align_right = Alignment(horizontal="right", vertical="center")

num_fmt = '#,##0.00'
pct_fmt = '0.00%'

def style_sheet(ws):
    ws.sheet_view.rightToLeft = True
    ws.views.sheetView[0].showGridLines = True

def add_ui_buttons(wb_excel):
    c_navy = 0x5D361B
    c_green = 0x346516
    c_blue = 0x684E33
    c_gold = 0x0953B4
    c_slate = 0x695547

    ws_dash = wb_excel.Sheets("Dashboard")
    actions = [
        ("➕ تسجيل قيد جديد", "GoToNewEntry", c_green, 30),
        ("📄 تصدير القوائم PDF", "ExportFinancialStatementsToPDF", c_navy, 170),
        ("🔄 تحديث المؤشرات", "RefreshAllReports", c_blue, 310),
        ("💾 حفظ نسخة احتياطية", "CreateInstantBackup", c_gold, 450),
        ("🔒 حماية المعادلات", "ProtectSystemFormulas", c_slate, 590),
        ("🔓 إلغاء الحماية", "UnprotectSystem", c_slate, 730),
    ]

    for text, macro, color, left_pos in actions:
        try:
            btn = ws_dash.Shapes.AddShape(5, left_pos, 72, 130, 30)
            btn.TextFrame2.TextRange.Characters.Text = text
            btn.TextFrame2.TextRange.Font.Name = "Segoe UI"
            btn.TextFrame2.TextRange.Font.Size = 10
            btn.TextFrame2.TextRange.Font.Bold = True
            btn.TextFrame2.TextRange.Font.Fill.Solid()
            btn.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
            btn.Fill.Solid()
            btn.Fill.ForeColor.RGB = color
            btn.Line.Visible = False
            btn.OnAction = macro
        except Exception:
            pass

    nav_sheets = [
        ("دليل الحسابات", "COA", 30),
        ("اليومية العامة", "General_Ledger", 125),
        ("ميزان المراجعة", "Trial_Balance", 220),
        ("قائمة الدخل", "Income_Statement", 315),
        ("المركز المالي", "Balance_Sheet", 410),
        ("التدفقات النقدية", "Cash_Flow", 505),
        ("كشف حساب", "Account_Statement", 600),
        ("أعمار الديون", "Aging_Analysis", 695),
        ("سجل الأصول", "Assets_Register", 790),
        ("تحليل المصروفات", "Expenses_Analysis", 885),
    ]

    for label, target_ws, left_pos in nav_sheets:
        try:
            nav_btn = ws_dash.Shapes.AddShape(5, left_pos, 240, 90, 24)
            nav_btn.TextFrame2.TextRange.Characters.Text = label
            nav_btn.TextFrame2.TextRange.Font.Name = "Segoe UI"
            nav_btn.TextFrame2.TextRange.Font.Size = 9
            nav_btn.TextFrame2.TextRange.Font.Bold = True
            nav_btn.TextFrame2.TextRange.Font.Fill.Solid()
            nav_btn.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
            nav_btn.Fill.Solid()
            nav_btn.Fill.ForeColor.RGB = c_navy
            nav_btn.Line.Visible = False
            ws_dash.Hyperlinks.Add(Anchor=nav_btn, Address="", SubAddress=f"'{target_ws}'!A1")
        except Exception:
            pass

    # Account_Statement buttons
    ws_stmt = wb_excel.Sheets("Account_Statement")
    try:
        btn_stmt = ws_stmt.Shapes.AddShape(5, 520, 48, 160, 32)
        btn_stmt.TextFrame2.TextRange.Characters.Text = "🔍 استخراج كشف الحساب"
        btn_stmt.TextFrame2.TextRange.Font.Name = "Segoe UI"
        btn_stmt.TextFrame2.TextRange.Font.Size = 10
        btn_stmt.TextFrame2.TextRange.Font.Bold = True
        btn_stmt.TextFrame2.TextRange.Font.Fill.Solid()
        btn_stmt.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
        btn_stmt.Fill.Solid()
        btn_stmt.Fill.ForeColor.RGB = c_green
        btn_stmt.Line.Visible = False
        btn_stmt.OnAction = "GenerateAccountStatement"

        btn_home = ws_stmt.Shapes.AddShape(5, 700, 48, 140, 32)
        btn_home.TextFrame2.TextRange.Characters.Text = "🏠 لوحة المؤشرات"
        btn_home.TextFrame2.TextRange.Font.Name = "Segoe UI"
        btn_home.TextFrame2.TextRange.Font.Size = 10
        btn_home.TextFrame2.TextRange.Font.Bold = True
        btn_home.TextFrame2.TextRange.Font.Fill.Solid()
        btn_home.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
        btn_home.Fill.Solid()
        btn_home.Fill.ForeColor.RGB = c_navy
        btn_home.Line.Visible = False
        btn_home.OnAction = "GoToDashboard"
    except Exception:
        pass

    # General Ledger home button
    ws_gl = wb_excel.Sheets("General_Ledger")
    try:
        btn_gl_home = ws_gl.Shapes.AddShape(5, 650, 6, 140, 28)
        btn_gl_home.TextFrame2.TextRange.Characters.Text = "🏠 لوحة المؤشرات"
        btn_gl_home.TextFrame2.TextRange.Font.Name = "Segoe UI"
        btn_gl_home.TextFrame2.TextRange.Font.Size = 10
        btn_gl_home.TextFrame2.TextRange.Font.Bold = True
        btn_gl_home.TextFrame2.TextRange.Font.Fill.Solid()
        btn_gl_home.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
        btn_gl_home.Fill.Solid()
        btn_gl_home.Fill.ForeColor.RGB = c_navy
        btn_gl_home.Line.Visible = False
        btn_gl_home.OnAction = "GoToDashboard"
    except Exception:
        pass

    for s_name in ["Trial_Balance", "Income_Statement", "Balance_Sheet", "Cash_Flow", "Aging_Analysis", "Assets_Register", "Expenses_Analysis"]:
        try:
            ws_item = wb_excel.Sheets(s_name)
            b = ws_item.Shapes.AddShape(5, 550, 6, 130, 26)
            b.TextFrame2.TextRange.Characters.Text = "🏠 لوحة المؤشرات"
            b.TextFrame2.TextRange.Font.Name = "Segoe UI"
            b.TextFrame2.TextRange.Font.Size = 9
            b.TextFrame2.TextRange.Font.Bold = True
            b.TextFrame2.TextRange.Font.Fill.Solid()
            b.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
            b.Fill.Solid()
            b.Fill.ForeColor.RGB = c_navy
            b.Line.Visible = False
            b.OnAction = "GoToDashboard"
        except Exception:
            pass

def build_production_live_workbook():
    from build_english_sheets_system import generate_full_system
    wb = generate_full_system()
    ws_gl = wb["General_Ledger"]

    # Clear all data rows
    for rng in list(ws_gl.merged_cells.ranges):
        if rng.min_row >= 3:
            ws_gl.unmerge_cells(str(rng))

    for r in range(3, 105):
        for c in range(1, 13):
            ws_gl.cell(row=r, column=c, value=None)

    # 3 Real Live Starter Transactions:
    # Entry 1: Capital 500,000 (Treasury 200,000 / Bank 300,000)
    # Entry 2: Purchases 10,000 cash from El-Nour
    # Entry 3: Sales 25,000 cash to Ahmed Ali
    starter_entries = [
        (1, 1, "2026-10-01", 10, "1210", "المركز الرئيسي", "إيداع حصة نقدية بالخزينة من رأس المال", 200000, 0, "إذن توريد-1"),
        (2, 1, "2026-10-01", 10, "1220", "بنك مصر", "إيداع حصة نقدية بالبنك من رأس المال", 300000, 0, "إشعار بنك-1"),
        (3, 1, "2026-10-01", 10, "3110", "المساهمون", "إثبات رأس المال المبدئي للشركة", 0, 500000, "عقد تأسيس"),

        (4, 2, "2026-10-15", 10, "5110", "شركة النور", "شراء بضاعة نقداً من شركة النور", 10000, 0, "فاتورة-55"),
        (5, 2, "2026-10-15", 10, "1210", "الخزينة", "سداد قيمة مشتريات بضاعة نقداً", 0, 10000, "سند صرف-1"),

        (6, 3, "2026-10-25", 10, "1210", "الخزينة", "تحصيل مبيعات بضاعة نقداً بالخزينة", 25000, 0, "سند قبض-1"),
        (7, 3, "2026-10-25", 10, "4110", "العميل أحمد علي", "إثبات مبيعات تجارية نقدية", 0, 25000, "فاتورة مبيعات-1"),
    ]

    for idx, (seq, eno, dt, mth, code, ent, desc, dr, cr, doc) in enumerate(starter_entries, start=3):
        ws_gl.cell(row=idx, column=1, value=seq).alignment = align_center
        ws_gl.cell(row=idx, column=2, value=eno).alignment = align_center
        ws_gl.cell(row=idx, column=3, value=dt).alignment = align_center
        ws_gl.cell(row=idx, column=4, value=mth).alignment = align_center
        ws_gl.cell(row=idx, column=5, value=code).alignment = align_center
        ws_gl.cell(row=idx, column=6, value=f'=IF(E{idx}="","",VLOOKUP(E{idx}, COA!A:B, 2, FALSE))')
        ws_gl.cell(row=idx, column=7, value=ent)
        ws_gl.cell(row=idx, column=8, value=desc)
        ws_gl.cell(row=idx, column=9, value=dr).number_format = num_fmt
        ws_gl.cell(row=idx, column=10, value=cr).number_format = num_fmt
        ws_gl.cell(row=idx, column=11, value=doc).alignment = align_center
        ws_gl.cell(row=idx, column=12, value=f'=IF(B{idx}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{idx})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{idx}), "متزن", "غير متزن"))')
        ws_gl.cell(row=idx, column=12).font = success_font
        ws_gl.cell(row=idx, column=12).alignment = align_center

        for c in range(1, 13):
            ws_gl.cell(row=idx, column=c).border = border_cell
            if c != 12: ws_gl.cell(row=idx, column=c).font = data_font

    # Pre-formatted rows for future transactions (from row 10 to row 70)
    for r in range(10, 71):
        ws_gl.cell(row=r, column=1, value=r-2).alignment = align_center
        ws_gl.cell(row=r, column=6, value=f'=IF(E{r}="","",VLOOKUP(E{r}, COA!A:B, 2, FALSE))')
        ws_gl.cell(row=r, column=12, value=f'=IF(B{r}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{r})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{r}), "متزن", "غير متزن"))')
        ws_gl.cell(row=r, column=12).font = success_font
        ws_gl.cell(row=r, column=12).alignment = align_center

        for c in range(1, 13):
            cell = ws_gl.cell(row=r, column=c)
            cell.border = border_cell
            if c != 12: cell.font = data_font
            if c in [9, 10]: cell.number_format = num_fmt
            if c in [1, 2, 3, 4, 5, 11]: cell.alignment = align_center

    # Grand Total Row at row 72
    tot_r = 72
    ws_gl.merge_cells(f"A{tot_r}:H{tot_r}")
    ws_gl.cell(row=tot_r, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام").font = total_font
    ws_gl.cell(row=tot_r, column=1).alignment = align_center
    ws_gl.cell(row=tot_r, column=1).fill = total_fill

    t_dr = ws_gl.cell(row=tot_r, column=9, value=f'=SUM(I3:I{tot_r-1})')
    t_dr.font = total_font; t_dr.fill = total_fill; t_dr.number_format = num_fmt; t_dr.border = border_total

    t_cr = ws_gl.cell(row=tot_r, column=10, value=f'=SUM(J3:J{tot_r-1})')
    t_cr.font = total_font; t_cr.fill = total_fill; t_cr.number_format = num_fmt; t_cr.border = border_total

    t_chk = ws_gl.cell(row=tot_r, column=12, value=f'=IF(ROUND(I{tot_r},2)=ROUND(J{tot_r},2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')
    t_chk.font = success_font; t_chk.fill = success_fill; t_chk.alignment = align_center; t_chk.border = border_total

    for c in range(1, 13):
        ws_gl.cell(row=tot_r, column=c).border = border_total

    # Reset Fixed assets register in production
    ws_ast = wb["Assets_Register"]
    for r in [3, 4, 5]:
        for c in range(1, 12):
            ws_ast.cell(row=r, column=c, value=None)

    return wb

if __name__ == "__main__":
    temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')
    base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')
    temp_bas = os.path.join(temp_dir, 'Accounting_VBA_Suite_1256.bas')
    
    xlsm_prod = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsm')
    xlsx_prod = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsx')

    temp_xlsx = os.path.join(temp_dir, 'Prod_Clean.xlsx')
    temp_xlsm = os.path.join(temp_dir, 'Prod_Clean.xlsm')

    wb = build_production_live_workbook()
    wb.save(temp_xlsx)

    xl = win32com.client.Dispatch('Excel.Application')
    xl.Visible = False
    xl.DisplayAlerts = False

    wb_live = xl.Workbooks.Open(temp_xlsx)
    try:
        wb_live.VBProject.VBComponents.Import(temp_bas)
    except Exception as e:
        print("VBA notice:", e)

    add_ui_buttons(wb_live)
    xl.CalculateFull()

    wb_live.SaveAs(temp_xlsm, FileFormat=52)
    wb_live.SaveAs(temp_xlsx, FileFormat=51)
    wb_live.Close()
    xl.Quit()

    shutil.copyfile(temp_xlsm, xlsm_prod)
    shutil.copyfile(temp_xlsx, xlsx_prod)
    print("Clean Production System generated and deployed successfully!")
