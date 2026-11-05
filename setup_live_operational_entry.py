# -*- coding: utf-8 -*-
"""
Sets up clean, live operational entries in the Production system
with automated VLOOKUP name lookup and smart balance formulas.
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

base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')
temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')

xlsm_prod = os.path.join(base_dir, "النظام_المحاسبي_التشغيلي_الفارغ.xlsm")
xlsx_prod = os.path.join(base_dir, "النظام_المحاسبي_التشغيلي_الفارغ.xlsx")
temp_xlsx = os.path.join(temp_dir, "Prod_Live.xlsx")
temp_xlsm = os.path.join(temp_dir, "Prod_Live.xlsm")
bas_file = os.path.join(base_dir, "Accounting_VBA_Suite.bas")

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
align_right = Alignment(horizontal="right", vertical="center")

wb = openpyxl.load_workbook(xlsx_prod)
ws_gl = wb["General_Ledger"]

# Unmerge any previous merged ranges in the data area
for rng in list(ws_gl.merged_cells.ranges):
    if rng.min_row >= 3:
        ws_gl.unmerge_cells(str(rng))

# Clear any previous rows from row 3 to row 105
for r in range(3, 105):
    for c in range(1, 13):
        ws_gl.cell(row=r, column=c, value=None)

# Live starter transactions demonstrating real operation:
# 1. Capital deposit: 500,000 (Treasury: 200,000 Dr / Bank: 300,000 Dr / Capital: 500,000 Cr)
# 2. Purchase of goods: 10,000 (Purchases: 10,000 Dr / Treasury: 10,000 Cr)
# 3. Cash sales: 25,000 (Treasury: 25,000 Dr / Sales: 25,000 Cr)

live_entries = [
    # Seq, EntryNo, Date, Month, Code, NameFormula, Entity, Desc, Debit, Credit, DocRef, BalanceFormula
    (1, 1, "2026-10-01", 10, "1210", '=IF(E3="","",VLOOKUP(E3, COA!A:B, 2, FALSE))', "المركز الرئيسي", "إيداع حصة نقدية بالخزينة من رأس المال", 200000, 0, "إذن توريد-1"),
    (2, 1, "2026-10-01", 10, "1220", '=IF(E4="","",VLOOKUP(E4, COA!A:B, 2, FALSE))', "بنك مصر", "إيداع حصة نقدية بالبنك من رأس المال", 300000, 0, "إشعار بنك-1"),
    (3, 1, "2026-10-01", 10, "3110", '=IF(E5="","",VLOOKUP(E5, COA!A:B, 2, FALSE))', "المساهمون", "إثبات رأس المال المبدئي للشركة", 0, 500000, "عقد تأسيس"),

    (4, 2, "2026-10-15", 10, "5110", '=IF(E6="","",VLOOKUP(E6, COA!A:B, 2, FALSE))', "شركة النور", "شراء بضاعة نقداً من شركة النور", 10000, 0, "فاتورة-55"),
    (5, 2, "2026-10-15", 10, "1210", '=IF(E7="","",VLOOKUP(E7, COA!A:B, 2, FALSE))', "الخزينة", "سداد قيمة مشتريات بضاعة نقداً", 0, 10000, "سند صرف-1"),

    (6, 3, "2026-10-25", 10, "1210", '=IF(E8="","",VLOOKUP(E8, COA!A:B, 2, FALSE))', "الخزينة", "تحصيل مبيعات بضاعة نقداً بالخزينة", 25000, 0, "سند قبض-1"),
    (7, 3, "2026-10-25", 10, "4110", '=IF(E9="","",VLOOKUP(E9, COA!A:B, 2, FALSE))', "العميل أحمد علي", "إثبات مبيعات تجارية نقدية", 0, 25000, "فاتورة مبيعات-1"),
]

for idx, row_data in enumerate(live_entries, start=3):
    seq, entry_no, dt, mth, code, name_f, entity, desc, dr, cr, doc = row_data
    ws_gl.cell(row=idx, column=1, value=seq).alignment = align_center
    ws_gl.cell(row=idx, column=2, value=entry_no).alignment = align_center
    ws_gl.cell(row=idx, column=3, value=dt).alignment = align_center
    ws_gl.cell(row=idx, column=4, value=mth).alignment = align_center
    ws_gl.cell(row=idx, column=5, value=code).alignment = align_center
    ws_gl.cell(row=idx, column=6, value=name_f)
    ws_gl.cell(row=idx, column=7, value=entity)
    ws_gl.cell(row=idx, column=8, value=desc)
    ws_gl.cell(row=idx, column=9, value=dr).number_format = '#,##0.00'
    ws_gl.cell(row=idx, column=10, value=cr).number_format = '#,##0.00'
    ws_gl.cell(row=idx, column=11, value=doc).alignment = align_center
    
    # Balance formula
    ws_gl.cell(row=idx, column=12, value=f'=IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{idx})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{idx}), "متزن", "غير متزن")')
    ws_gl.cell(row=idx, column=12).font = success_font
    ws_gl.cell(row=idx, column=12).alignment = align_center

    for c in range(1, 13):
        ws_gl.cell(row=idx, column=c).border = border_cell
        if c not in [12]: ws_gl.cell(row=idx, column=c).font = data_font

# Pre-format rows 10 to 60 for seamless future entry
for r in range(10, 60):
    ws_gl.cell(row=r, column=1, value=r-2).alignment = align_center
    ws_gl.cell(row=r, column=6, value=f'=IF(E{r}="","",VLOOKUP(E{r}, COA!A:B, 2, FALSE))')
    ws_gl.cell(row=r, column=12, value=f'=IF(B{r}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{r})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{r}), "متزن", "غير متزن"))')
    ws_gl.cell(row=r, column=12).font = success_font
    ws_gl.cell(row=r, column=12).alignment = align_center

    for c in range(1, 13):
        cell = ws_gl.cell(row=r, column=c)
        cell.border = border_cell
        if c not in [12]: cell.font = data_font
        if c in [9, 10]: cell.number_format = '#,##0.00'
        if c in [1, 2, 3, 4, 5, 11]: cell.alignment = align_center

# Grand Total Row at Row 61
tot_row = 61
ws_gl.merge_cells(f"A{tot_row}:H{tot_row}")
ws_gl.cell(row=tot_row, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام").font = total_font
ws_gl.cell(row=tot_row, column=1).alignment = align_center
ws_gl.cell(row=tot_row, column=1).fill = total_fill

t_dr = ws_gl.cell(row=tot_row, column=9, value=f'=SUM(I3:I{tot_row-1})')
t_dr.font = total_font; t_dr.fill = total_fill; t_dr.number_format = '#,##0.00'; t_dr.border = border_total

t_cr = ws_gl.cell(row=tot_row, column=10, value=f'=SUM(J3:J{tot_row-1})')
t_cr.font = total_font; t_cr.fill = total_fill; t_cr.number_format = '#,##0.00'; t_cr.border = border_total

t_chk = ws_gl.cell(row=tot_row, column=12, value=f'=IF(ROUND(I{tot_row},2)=ROUND(J{tot_row},2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')
t_chk.font = success_font; t_chk.fill = success_fill; t_chk.alignment = align_center; t_chk.border = border_total

for c in range(1, 13):
    ws_gl.cell(row=tot_row, column=c).border = border_total

wb.save(temp_xlsx)
print("Temp live XLSX saved.")

# Re-open in Excel COM to recalculate and embed VBA & buttons cleanly
xl = win32com.client.Dispatch("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False

from run_full_english_migration import add_buttons

wb_live = xl.Workbooks.Open(temp_xlsx)
try:
    wb_live.VBProject.VBComponents.Import(bas_file)
except Exception as e:
    print("VBA notice:", e)

add_buttons(wb_live)
xl.CalculateFull()

wb_live.SaveAs(temp_xlsm, FileFormat=52)
wb_live.SaveAs(temp_xlsx, FileFormat=51)
wb_live.Close()
xl.Quit()

shutil.copyfile(temp_xlsm, xlsm_prod)
shutil.copyfile(temp_xlsx, xlsx_prod)

print("SUCCESS: Live production system created and updated!")
