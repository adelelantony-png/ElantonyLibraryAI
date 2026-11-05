# -*- coding: utf-8 -*-
"""
Fix production live workbook:
Completely wipes rows 10 to 105 in General_Ledger and sets up
the 3 starter entries cleanly, with grand total right below them.
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
from build_clean_production_live import add_ui_buttons

base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')
temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')
temp_bas = os.path.join(temp_dir, 'Accounting_VBA_Suite_1256.bas')

xlsm_prod = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsm')
xlsx_prod = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsx')
temp_xlsx = os.path.join(temp_dir, 'Prod_Clean2.xlsx')
temp_xlsm = os.path.join(temp_dir, 'Prod_Clean2.xlsm')

font_family = "Segoe UI"
data_font = Font(name=font_family, size=10, bold=False, color="1E293B")
data_bold = Font(name=font_family, size=10, bold=True, color="1E293B")
total_font = Font(name=font_family, size=10, bold=True, color="0F172A")
success_font = Font(name=font_family, size=10, bold=True, color="166534")

thin_gray = Side(style='thin', color='CBD5E1')
double_bottom = Side(style='double', color='0F172A')

border_cell = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
border_total = Border(top=thin_gray, bottom=double_bottom, left=thin_gray, right=thin_gray)

total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
success_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")

align_center = Alignment(horizontal="center", vertical="center")

wb = openpyxl.load_workbook(xlsx_prod)
ws_gl = wb["General_Ledger"]

# Unmerge all data rows
for rng in list(ws_gl.merged_cells.ranges):
    if rng.min_row >= 3:
        ws_gl.unmerge_cells(str(rng))

# Completely wipe all rows from 3 to 120
for r in range(3, 125):
    for c in range(1, 13):
        ws_gl.cell(row=r, column=c, value=None)

# 3 Real Live Starter Transactions
live_entries = [
    (1, 1, "2026-10-01", 10, "1210", "المركز الرئيسي", "إيداع حصة نقدية بالخزينة من رأس المال", 200000, 0, "إذن توريد-1"),
    (2, 1, "2026-10-01", 10, "1220", "بنك مصر", "إيداع حصة نقدية بالبنك من رأس المال", 300000, 0, "إشعار بنك-1"),
    (3, 1, "2026-10-01", 10, "3110", "المساهمون", "إثبات رأس المال المبدئي للشركة", 0, 500000, "عقد تأسيس"),

    (4, 2, "2026-10-15", 10, "5110", "شركة النور", "شراء بضاعة نقداً من شركة النور", 10000, 0, "فاتورة-55"),
    (5, 2, "2026-10-15", 10, "1210", "الخزينة", "سداد قيمة مشتريات بضاعة نقداً", 0, 10000, "سند صرف-1"),

    (6, 3, "2026-10-25", 10, "1210", "الخزينة", "تحصيل مبيعات بضاعة نقداً بالخزينة", 25000, 0, "سند قبض-1"),
    (7, 3, "2026-10-25", 10, "4110", "العميل أحمد علي", "إثبات مبيعات تجارية نقدية", 0, 25000, "فاتورة مبيعات-1"),
]

for idx, (seq, eno, dt, mth, code, ent, desc, dr, cr, doc) in enumerate(live_entries, start=3):
    ws_gl.cell(row=idx, column=1, value=seq).alignment = align_center
    ws_gl.cell(row=idx, column=2, value=eno).alignment = align_center
    ws_gl.cell(row=idx, column=3, value=dt).alignment = align_center
    ws_gl.cell(row=idx, column=4, value=mth).alignment = align_center
    ws_gl.cell(row=idx, column=5, value=code).alignment = align_center
    ws_gl.cell(row=idx, column=6, value=f'=IF(E{idx}="","",VLOOKUP(E{idx}, COA!A:B, 2, FALSE))')
    ws_gl.cell(row=idx, column=7, value=ent)
    ws_gl.cell(row=idx, column=8, value=desc)
    ws_gl.cell(row=idx, column=9, value=dr).number_format = '#,##0.00'
    ws_gl.cell(row=idx, column=10, value=cr).number_format = '#,##0.00'
    ws_gl.cell(row=idx, column=11, value=doc).alignment = align_center
    ws_gl.cell(row=idx, column=12, value=f'=IF(B{idx}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{idx})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{idx}), "متزن", "غير متزن"))')
    ws_gl.cell(row=idx, column=12).font = success_font
    ws_gl.cell(row=idx, column=12).alignment = align_center

    for c in range(1, 13):
        ws_gl.cell(row=idx, column=c).border = border_cell
        if c != 12: ws_gl.cell(row=idx, column=c).font = data_font

# Pre-format rows 10 to 60 for future entries (empty cells with formula triggers)
for r in range(10, 61):
    ws_gl.cell(row=r, column=1, value=r-2).alignment = align_center
    ws_gl.cell(row=r, column=6, value=f'=IF(E{r}="","",VLOOKUP(E{r}, COA!A:B, 2, FALSE))')
    ws_gl.cell(row=r, column=12, value=f'=IF(B{r}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{r})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{r}), "متزن", "غير متزن"))')
    ws_gl.cell(row=r, column=12).font = success_font
    ws_gl.cell(row=r, column=12).alignment = align_center

    for c in range(1, 13):
        cell = ws_gl.cell(row=r, column=c)
        cell.border = border_cell
        if c != 12: cell.font = data_font
        if c in [9, 10]: cell.number_format = '#,##0.00'
        if c in [1, 2, 3, 4, 5, 11]: cell.alignment = align_center

# Grand Total Row at row 62
tot_r = 62
ws_gl.merge_cells(f"A{tot_r}:H{tot_r}")
ws_gl.cell(row=tot_r, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام").font = total_font
ws_gl.cell(row=tot_r, column=1).alignment = align_center
ws_gl.cell(row=tot_r, column=1).fill = total_fill

t_dr = ws_gl.cell(row=tot_r, column=9, value=f'=SUM(I3:I{tot_r-1})')
t_dr.font = total_font; t_dr.fill = total_fill; t_dr.number_format = '#,##0.00'; t_dr.border = border_total

t_cr = ws_gl.cell(row=tot_r, column=10, value=f'=SUM(J3:J{tot_r-1})')
t_cr.font = total_font; t_cr.fill = total_fill; t_cr.number_format = '#,##0.00'; t_cr.border = border_total

t_chk = ws_gl.cell(row=tot_r, column=12, value=f'=IF(ROUND(I{tot_r},2)=ROUND(J{tot_r},2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')
t_chk.font = success_font; t_chk.fill = success_fill; t_chk.alignment = align_center; t_chk.border = border_total

for c in range(1, 13):
    ws_gl.cell(row=tot_r, column=c).border = border_total

wb.save(temp_xlsx)

# Run in Excel COM to recalculate and embed VBA
xl = win32com.client.Dispatch('Excel.Application')
xl.Visible = False
xl.DisplayAlerts = False

wb_live = xl.Workbooks.Open(temp_xlsx)
try:
    for comp in list(wb_live.VBProject.VBComponents):
        if comp.Name == "Accounting_VBA_Suite":
            wb_live.VBProject.VBComponents.Remove(comp)
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
print("SUCCESS: Live production system wiped and cleanly re-created!")
