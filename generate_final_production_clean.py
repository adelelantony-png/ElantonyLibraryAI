# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
import openpyxl
import win32com.client

base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')
temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')
temp_bas = os.path.join(temp_dir, 'Accounting_VBA_Suite_1256.bas')

bench_xlsx = os.path.join(base_dir, 'النظام_المحاسبي_المتقدم_الشامل.xlsx')
prod_xlsx = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsx')
prod_xlsm = os.path.join(base_dir, 'النظام_المحاسبي_التشغيلي_الفارغ.xlsm')

temp_xlsx = os.path.join(temp_dir, 'Standalone_Prod.xlsx')
temp_xlsm = os.path.join(temp_dir, 'Standalone_Prod.xlsm')

# 1. Load benchmark workbook as base template
wb = openpyxl.load_workbook(bench_xlsx)
ws_gl = wb['General_Ledger']

# Unmerge all cells below row 2
for rng in list(ws_gl.merged_cells.ranges):
    if rng.min_row >= 3:
        ws_gl.unmerge_cells(str(rng))

# Completely delete rows 3 to 150
ws_gl.delete_rows(3, 150)

# Now insert the 3 clean live starter transactions
starter_data = [
    (1, 1, "2026-10-01", 10, "1210", '=IF(E3="","",VLOOKUP(E3, COA!A:B, 2, FALSE))', "المركز الرئيسي", "إيداع حصة نقدية بالخزينة من رأس المال", 200000, 0, "إذن توريد-1", '=IF(B3="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B3)=SUMIFS($J$3:$J$100, $B$3:$B$100, B3), "متزن", "غير متزن"))'),
    (2, 1, "2026-10-01", 10, "1220", '=IF(E4="","",VLOOKUP(E4, COA!A:B, 2, FALSE))', "بنك مصر", "إيداع حصة نقدية بالبنك من رأس المال", 300000, 0, "إشعار بنك-1", '=IF(B4="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B4)=SUMIFS($J$3:$J$100, $B$3:$B$100, B4), "متزن", "غير متزن"))'),
    (3, 1, "2026-10-01", 10, "3110", '=IF(E5="","",VLOOKUP(E5, COA!A:B, 2, FALSE))', "المساهمون", "إثبات رأس المال المبدئي للشركة", 0, 500000, "عقد تأسيس", '=IF(B5="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B5)=SUMIFS($J$3:$J$100, $B$3:$B$100, B5), "متزن", "غير متزن"))'),

    (4, 2, "2026-10-15", 10, "5110", '=IF(E6="","",VLOOKUP(E6, COA!A:B, 2, FALSE))', "شركة النور", "شراء بضاعة نقداً من شركة النور", 10000, 0, "فاتورة-55", '=IF(B6="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B6)=SUMIFS($J$3:$J$100, $B$3:$B$100, B6), "متزن", "غير متزن"))'),
    (5, 2, "2026-10-15", 10, "1210", '=IF(E7="","",VLOOKUP(E7, COA!A:B, 2, FALSE))', "الخزينة", "سداد قيمة مشتريات بضاعة نقداً", 0, 10000, "سند صرف-1", '=IF(B7="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B7)=SUMIFS($J$3:$J$100, $B$3:$B$100, B7), "متزن", "غير متزن"))'),

    (6, 3, "2026-10-25", 10, "1210", '=IF(E8="","",VLOOKUP(E8, COA!A:B, 2, FALSE))', "الخزينة", "تحصيل مبيعات بضاعة نقداً بالخزينة", 25000, 0, "سند قبض-1", '=IF(B8="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B8)=SUMIFS($J$3:$J$100, $B$3:$B$100, B8), "متزن", "غير متزن"))'),
    (7, 3, "2026-10-25", 10, "4110", '=IF(E9="","",VLOOKUP(E9, COA!A:B, 2, FALSE))', "العميل أحمد علي", "إثبات مبيعات تجارية نقدية", 0, 25000, "فاتورة مبيعات-1", '=IF(B9="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B9)=SUMIFS($J$3:$J$100, $B$3:$B$100, B9), "متزن", "غير متزن"))'),
]

font_family = "Segoe UI"
data_font = openpyxl.styles.Font(name=font_family, size=10, bold=False, color="1E293B")
total_font = openpyxl.styles.Font(name=font_family, size=10, bold=True, color="0F172A")
success_font = openpyxl.styles.Font(name=font_family, size=10, bold=True, color="166534")

thin_gray = openpyxl.styles.Side(style='thin', color='CBD5E1')
double_bottom = openpyxl.styles.Side(style='double', color='0F172A')
border_cell = openpyxl.styles.Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)
border_total = openpyxl.styles.Border(top=thin_gray, bottom=double_bottom, left=thin_gray, right=thin_gray)

total_fill = openpyxl.styles.PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
success_fill = openpyxl.styles.PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")

for r_idx, row in enumerate(starter_data, start=3):
    for c_idx, val in enumerate(row, start=1):
        cell = ws_gl.cell(row=r_idx, column=c_idx, value=val)
        cell.border = border_cell
        cell.font = data_font
        if c_idx in [1, 2, 3, 4, 5, 11]:
            cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")
        elif c_idx in [9, 10]:
            cell.number_format = '#,##0.00'
        elif c_idx == 12:
            cell.font = success_font
            cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

# Pre-format rows 10 to 60 for future entries
for r in range(10, 61):
    ws_gl.cell(row=r, column=1, value=r-2).alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")
    ws_gl.cell(row=r, column=6, value=f'=IF(E{r}="","",VLOOKUP(E{r}, COA!A:B, 2, FALSE))')
    ws_gl.cell(row=r, column=12, value=f'=IF(B{r}="","",IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{r})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{r}), "متزن", "غير متزن"))')
    ws_gl.cell(row=r, column=12).font = success_font
    ws_gl.cell(row=r, column=12).alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

    for c in range(1, 13):
        cell = ws_gl.cell(row=r, column=c)
        cell.border = border_cell
        if c != 12: cell.font = data_font
        if c in [9, 10]: cell.number_format = '#,##0.00'
        if c in [1, 2, 3, 4, 5, 11]: cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

# Grand total at row 62
tot_r = 62
ws_gl.merge_cells(f"A{tot_r}:H{tot_r}")
t_lbl = ws_gl.cell(row=tot_r, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام")
t_lbl.font = total_font; t_lbl.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center"); t_lbl.fill = total_fill

t_dr = ws_gl.cell(row=tot_r, column=9, value=f'=SUM(I3:I{tot_r-1})')
t_dr.font = total_font; t_dr.fill = total_fill; t_dr.number_format = '#,##0.00'; t_dr.border = border_total

t_cr = ws_gl.cell(row=tot_r, column=10, value=f'=SUM(J3:J{tot_r-1})')
t_cr.font = total_font; t_cr.fill = total_fill; t_cr.number_format = '#,##0.00'; t_cr.border = border_total

t_chk = ws_gl.cell(row=tot_r, column=12, value=f'=IF(ROUND(I{tot_r},2)=ROUND(J{tot_r},2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')
t_chk.font = success_font; t_chk.fill = success_fill; t_chk.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center"); t_chk.border = border_total

for c in range(1, 13):
    ws_gl.cell(row=tot_r, column=c).border = border_total

# Reset Fixed Assets Register in production
ws_ast = wb["Assets_Register"]
for r in [3, 4, 5]:
    for c in range(1, 12):
        ws_ast.cell(row=r, column=c, value=None)

wb.save(temp_xlsx)
print("Saved clean XLSX via delete_rows.")

# Now Excel COM processing
xl = win32com.client.Dispatch('Excel.Application')
xl.Visible = False
xl.DisplayAlerts = False

wb_com = xl.Workbooks.Open(temp_xlsx)
try:
    for comp in list(wb_com.VBProject.VBComponents):
        if comp.Name == 'Accounting_VBA_Suite':
            wb_com.VBProject.VBComponents.Remove(comp)
    wb_com.VBProject.VBComponents.Import(temp_bas)
    print("VBA imported cleanly.")
except Exception as e:
    print("VBA import:", e)

xl.CalculateFull()
wb_com.SaveAs(temp_xlsm, FileFormat=52)
wb_com.SaveAs(temp_xlsx, FileFormat=51)
wb_com.Close()
xl.Quit()

shutil.copyfile(temp_xlsm, prod_xlsm)
shutil.copyfile(temp_xlsx, prod_xlsx)
print("SUCCESS: Pure production system created!")
