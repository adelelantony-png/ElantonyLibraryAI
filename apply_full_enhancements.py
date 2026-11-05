# -*- coding: utf-8 -*-
"""
Script to apply all enhancements:
1. Shape action buttons on all sheets
2. Interactive navigation bar
3. VBA modules integration
4. Generating clean production template (النظام_المحاسبي_التشغيلي_الفارغ.xlsm)
5. Applying formula protection and backups folder
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
import openpyxl
import win32com.client

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

def add_buttons_and_navigation(wb_excel, is_production=False):
    # Colors (BGR for Excel COM)
    # Navy: RGB(27, 54, 93) -> BGR: 0x5D361B
    # Green: RGB(22, 101, 52) -> BGR: 0x346516
    # Blue: RGB(51, 78, 104) -> BGR: 0x684E33
    # Gold: RGB(180, 83, 9) -> BGR: 0x0953B4
    # Slate: RGB(71, 85, 105) -> BGR: 0x695547
    # Red/Crimson: RGB(153, 27, 27) -> BGR: 0x1B1B99

    c_navy = 0x5D361B
    c_green = 0x346516
    c_blue = 0x684E33
    c_gold = 0x0953B4
    c_slate = 0x695547

    # 1. Dashboard Buttons
    ws_dash = wb_excel.Sheets("لوحة_المؤشرات")
    
    # Action buttons at top (Row 3 area: Top ~ 70)
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
            btn = ws_dash.Shapes.AddShape(5, left_pos, 72, 130, 30) # 5 = msoShapeRoundedRectangle
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
            print(f"Notice button {text}: {e}")

    # Navigation buttons row in Dashboard (Row 11 area: Top ~ 260)
    nav_sheets = [
        ("دليل الحسابات", "دليل_الحسابات", 30),
        ("اليومية العامة", "اليومية_العامة", 125),
        ("ميزان المراجعة", "ميزان_المراجعة", 220),
        ("قائمة الدخل", "قائمة_الدخل", 315),
        ("المركز المالي", "المركز_المالي", 410),
        ("التدفقات النقدية", "التدفقات_النقدية", 505),
        ("كشف حساب", "كشف_حساب_ديناميكي", 600),
        ("أعمار الديون", "أعمار_الديون", 695),
        ("سجل الأصول", "سجل_الأصول_والإهلاك", 790),
        ("تحليل المصروفات", "تحليل_المصروفات_والربحية", 885),
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
            # Add hyperlink to sheet
            ws_dash.Hyperlinks.Add(Anchor=nav_btn, Address="", SubAddress=f"'{target_ws}'!A1")
        except Exception as e:
            pass

    # 2. Account Statement Buttons
    ws_stmt = wb_excel.Sheets("كشف_حساب_ديناميكي")
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
    except Exception as e:
        print("Error stmt buttons:", e)

    # 3. Fixed Assets Buttons
    ws_ast = wb_excel.Sheets("سجل_الأصول_والإهلاك")
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
    except Exception as e:
        print("Error ast buttons:", e)

    # 4. General Ledger Buttons
    ws_gl = wb_excel.Sheets("اليومية_العامة")
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
    except Exception as e:
        print("Error gl buttons:", e)

    # Return to home on all other reports
    for s_name in ["ميزان_المراجعة", "قائمة_الدخل", "المركز_المالي", "التدفقات_النقدية", "أعمار_الديون", "تحليل_المصروفات_والربحية"]:
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

print("Starting Enhancement Process...")

# Step 1: Enhance Benchmark XLSM
temp_xlsm_bench = os.path.join(temp_dir, "Bench_Enhanced.xlsm")
shutil.copyfile(xlsm_benchmark, temp_xlsm_bench)

xl = win32com.client.Dispatch("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False

wb = xl.Workbooks.Open(temp_xlsm_bench)

# Replace VBA module with updated suite
try:
    for comp in list(wb.VBProject.VBComponents):
        if comp.Name == "Accounting_VBA_Suite":
            wb.VBProject.VBComponents.Remove(comp)
    wb.VBProject.VBComponents.Import(temp_bas)
    print("VBA Suite updated in Benchmark XLSM.")
except Exception as e:
    print("VBA update notice:", e)

add_buttons_and_navigation(wb, is_production=False)
xl.CalculateFull()
wb.SaveAs(temp_xlsm_bench, FileFormat=52)
wb.Close()
shutil.copyfile(temp_xlsm_bench, xlsm_benchmark)
print("Benchmark XLSM updated with UI buttons and navigation.")

# Step 2: Generate the Pristine Production Template (نظام تشغيلي فارغ جاهز للمستقبل)
wb_prod = openpyxl.load_workbook(xlsx_benchmark)
ws_gl_prod = wb_prod["اليومية_العامة"]

# Clear journal data rows (from row 3 to 54), leave row 3 as empty starter row
for r in range(4, 55):
    for c in range(1, 13):
        ws_gl_prod.cell(row=r, column=c, value=None)

# Initialize row 3 with blanks
ws_gl_prod.cell(row=3, column=1, value=1) # Seq 1
for c in range(2, 12):
    ws_gl_prod.cell(row=3, column=c, value=None)

# Re-establish GL Total row at row 4
ws_gl_prod.cell(row=4, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام")
ws_gl_prod.cell(row=4, column=9, value="=SUM(I3:I3)")
ws_gl_prod.cell(row=4, column=10, value="=SUM(J3:J3)")
ws_gl_prod.cell(row=4, column=12, value='=IF(ROUND(I4,2)=ROUND(J4,2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')

# Clear fixed assets in production to let user add real assets
ws_ast_prod = wb_prod["سجل_الأصول_والإهلاك"]
for r in [3, 4, 5]:
    for c in range(1, 12):
        ws_ast_prod.cell(row=r, column=c, value=None)

temp_xlsx_prod = os.path.join(temp_dir, "Production.xlsx")
temp_xlsm_prod = os.path.join(temp_dir, "Production.xlsm")
wb_prod.save(temp_xlsx_prod)

# Open production with Excel COM, import VBA, add buttons, and save as XLSM and XLSX
wb_p = xl.Workbooks.Open(temp_xlsx_prod)
try:
    wb_p.VBProject.VBComponents.Import(temp_bas)
    print("VBA imported into Production template.")
except Exception as e:
    print("Production VBA import notice:", e)

add_buttons_and_navigation(wb_p, is_production=True)
xl.CalculateFull()
wb_p.SaveAs(temp_xlsm_prod, FileFormat=52) # xlsm
wb_p.SaveAs(temp_xlsx_prod, FileFormat=51) # xlsx
wb_p.Close()
xl.Quit()

shutil.copyfile(temp_xlsm_prod, xlsm_production)
shutil.copyfile(temp_xlsx_prod, xlsx_production)

print("SUCCESS: Both Benchmark and Production systems are ready!")
