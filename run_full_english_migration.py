# -*- coding: utf-8 -*-
"""
Main runner to migrate all workbooks to English sheet names with updated buttons & VBA.
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
import openpyxl
import win32com.client
from build_english_sheets_system import generate_full_system

temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')
base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')
backup_dir = os.path.join(base_dir, "Backups")
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

xlsx_benchmark = os.path.join(base_dir, "النظام_المحاسبي_المتقدم_الشامل.xlsx")
xlsm_benchmark = os.path.join(base_dir, "النظام_المحاسبي_المتقدم_الشامل.xlsm")
xlsm_production = os.path.join(base_dir, "النظام_المحاسبي_التشغيلي_الفارغ.xlsm")
xlsx_production = os.path.join(base_dir, "النظام_المحاسبي_التشغيلي_الفارغ.xlsx")
bas_file = os.path.join(base_dir, "Accounting_VBA_Suite.bas")

temp_bas = os.path.join(temp_dir, "Accounting_VBA_Suite.bas")
shutil.copyfile(bas_file, temp_bas)

def add_buttons(wb_excel):
    c_navy = 0x5D361B
    c_green = 0x346516
    c_blue = 0x684E33
    c_gold = 0x0953B4
    c_slate = 0x695547

    # 1. Dashboard
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
        except Exception as e:
            print("Notice:", e)

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

    # 2. Account_Statement
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

    # 3. Assets_Register
    ws_ast = wb_excel.Sheets("Assets_Register")
    try:
        btn_ast = ws_ast.Shapes.AddShape(5, 450, 6, 180, 28)
        btn_ast.TextFrame2.TextRange.Characters.Text = "⚡ ترحيل قيد الإهلاك آلياً"
        btn_ast.TextFrame2.TextRange.Font.Name = "Segoe UI"
        btn_ast.TextFrame2.TextRange.Font.Size = 10
        btn_ast.TextFrame2.TextRange.Font.Bold = True
        btn_ast.TextFrame2.TextRange.Font.Fill.Solid()
        btn_ast.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
        btn_ast.Fill.Solid()
        btn_ast.Fill.ForeColor.RGB = c_gold
        btn_ast.Line.Visible = False
        btn_ast.OnAction = "AutoGenerateDepreciationEntry"

        btn_home2 = ws_ast.Shapes.AddShape(5, 650, 6, 140, 28)
        btn_home2.TextFrame2.TextRange.Characters.Text = "🏠 لوحة المؤشرات"
        btn_home2.TextFrame2.TextRange.Font.Name = "Segoe UI"
        btn_home2.TextFrame2.TextRange.Font.Size = 10
        btn_home2.TextFrame2.TextRange.Font.Bold = True
        btn_home2.TextFrame2.TextRange.Font.Fill.Solid()
        btn_home2.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = 0xFFFFFF
        btn_home2.Fill.Solid()
        btn_home2.Fill.ForeColor.RGB = c_navy
        btn_home2.Line.Visible = False
        btn_home2.OnAction = "GoToDashboard"
    except Exception:
        pass

    # 4. General_Ledger
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

    for s_name in ["Trial_Balance", "Income_Statement", "Balance_Sheet", "Cash_Flow", "Aging_Analysis", "Expenses_Analysis"]:
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

# Step 1: Generate Benchmark Workbook with English sheets
wb_bench = generate_full_system()
temp_xlsx_bench = os.path.join(temp_dir, "Bench_En.xlsx")
temp_xlsm_bench = os.path.join(temp_dir, "Bench_En.xlsm")
wb_bench.save(temp_xlsx_bench)

# Step 2: Generate Production Workbook with English sheets
wb_prod = generate_full_system()
ws_gl_prod = wb_prod["General_Ledger"]
for r in range(4, 55):
    for c in range(1, 13):
        ws_gl_prod.cell(row=r, column=c, value=None)
ws_gl_prod.cell(row=3, column=1, value=1)
for c in range(2, 12):
    ws_gl_prod.cell(row=3, column=c, value=None)
ws_gl_prod.cell(row=4, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام")
ws_gl_prod.cell(row=4, column=9, value="=SUM(I3:I3)")
ws_gl_prod.cell(row=4, column=10, value="=SUM(J3:J3)")
ws_gl_prod.cell(row=4, column=12, value='=IF(ROUND(I4,2)=ROUND(J4,2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')

ws_ast_prod = wb_prod["Assets_Register"]
for r in [3, 4, 5]:
    for c in range(1, 12):
        ws_ast_prod.cell(row=r, column=c, value=None)

temp_xlsx_prod = os.path.join(temp_dir, "Prod_En.xlsx")
temp_xlsm_prod = os.path.join(temp_dir, "Prod_En.xlsm")
wb_prod.save(temp_xlsx_prod)

# Step 3: Excel COM to add VBA & Buttons to both
xl = win32com.client.Dispatch("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False

# Benchmark
wb_b = xl.Workbooks.Open(temp_xlsx_bench)
try:
    wb_b.VBProject.VBComponents.Import(temp_bas)
except Exception as e:
    print("VBA import bench notice:", e)
add_buttons(wb_b)
xl.CalculateFull()
wb_b.SaveAs(temp_xlsm_bench, FileFormat=52)
wb_b.SaveAs(temp_xlsx_bench, FileFormat=51)
import time
wb_b.Close()

# Production
wb_p = xl.Workbooks.Open(temp_xlsx_prod)
try:
    wb_p.VBProject.VBComponents.Import(temp_bas)
except Exception as e:
    print("VBA import prod notice:", e)
add_buttons(wb_p)
xl.CalculateFull()
wb_p.SaveAs(temp_xlsm_prod, FileFormat=52)
wb_p.SaveAs(temp_xlsx_prod, FileFormat=51)
wb_p.Close()

xl.Quit()
del wb_b
del wb_p
del xl
import time
time.sleep(2)

# Copy to final destinations
shutil.copyfile(temp_xlsm_bench, xlsm_benchmark)
shutil.copyfile(temp_xlsx_bench, xlsx_benchmark)
shutil.copyfile(temp_xlsm_prod, xlsm_production)
shutil.copyfile(temp_xlsx_prod, xlsx_production)

print("Migration to English Sheet Names completed successfully!")
