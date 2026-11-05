# -*- coding: utf-8 -*-
"""
Generator for the Advanced Enterprise Accounting System
Author: Google Deepmind Antigravity Pair Programmer
Company: شركة محمود خليفة للتجارة والاستيراد والتصدير (ش.م.م)
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_accounting_system():
    wb = openpyxl.Workbook()

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

    # Fills
    navy_dark = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    navy_light = PatternFill(start_color="2C4D75", end_color="2C4D75", fill_type="solid")
    slate_header = PatternFill(start_color="334E68", end_color="334E68", fill_type="solid")
    total_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    subtotal_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    kpi_card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    success_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    gold_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    # Borders
    thin_gray = Side(style='thin', color='CBD5E1')
    thick_navy = Side(style='medium', color='1B365D')
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

    # ==========================================
    # 1. لوحة المؤشرات المالية (Dashboard)
    # ==========================================
    ws_dash = wb.create_sheet("لوحة_المؤشرات", 0)
    style_sheet(ws_dash)

    ws_dash.merge_cells("A1:I1")
    ws_dash["A1"] = "نظام الإدارة المالية والمحاسبية المتقدم - شركة محمود خليفة للتجارة والاستيراد والتصدير (ش.م.م)"
    ws_dash["A1"].font = title_font
    ws_dash["A1"].fill = navy_dark
    ws_dash["A1"].alignment = align_center
    ws_dash.row_dimensions[1].height = 40

    ws_dash.merge_cells("A2:I2")
    ws_dash["A2"] = "لوحة المؤشرات التنفيذية ومتابعة الأداء المالي والسيولة - السنة المالية 2016"
    ws_dash["A2"].font = sub_title_font
    ws_dash["A2"].fill = navy_light
    ws_dash["A2"].alignment = align_center
    ws_dash.row_dimensions[2].height = 25

    kpis = [
        ("إجمالي الإيرادات", "=قائمة_الدخل!D7", "B4:C4", "B5:C5", "B6:C6"),
        ("تكلفة المبيعات", "=قائمة_الدخل!D12", "D4:E4", "D5:E5", "D6:E6"),
        ("مجمل الربح", "=قائمة_الدخل!D13", "F4:G4", "F5:G5", "F6:G6"),
        ("صافي الربح بعد الضريبة", "=قائمة_الدخل!D25", "H4:I4", "H5:I5", "H6:I6"),
        ("رصيد السيولة (خزينة وبنوك)", "=ميزان_المراجعة!H7+ميزان_المراجعة!H8", "B8:C8", "B9:C9", "B10:C10"),
        ("إجمالي الأصول", "=المركز_المالي!D14", "D8:E8", "D9:E9", "D10:E10"),
        ("رأس المال العامل (NWC)", "=المركز_المالي!D13-المركز_المالي!D25", "F8:G8", "F9:G9", "F10:G10"),
        ("نسبة التداول (Current Ratio)", "=المركز_المالي!D13/المركز_المالي!D25", "H8:I8", "H9:I9", "H10:I10")
    ]

    for title, formula, top_m, val_m, bot_m in kpis:
        top_cell = top_m.split(":")[0]
        val_cell = val_m.split(":")[0]
        ws_dash.merge_cells(top_m)
        ws_dash[top_cell] = title
        ws_dash[top_cell].font = kpi_lbl_font
        ws_dash[top_cell].alignment = align_center
        ws_dash[top_cell].fill = subtotal_fill

        ws_dash.merge_cells(val_m)
        ws_dash[val_cell] = formula
        ws_dash[val_cell].font = kpi_val_font
        ws_dash[val_cell].alignment = align_center
        ws_dash[val_cell].fill = kpi_card_fill
        if "Ratio" in title:
            ws_dash[val_cell].number_format = '0.00'
        elif "%" in title:
            ws_dash[val_cell].number_format = pct_fmt
        else:
            ws_dash[val_cell].number_format = num_fmt

        for r in range(int(top_m[1]), int(bot_m[1])+1):
            col1 = ord(top_m[0]) - 64
            col2 = ord(top_m.split(":")[1][0]) - 64
            for c in range(col1, col2+1):
                ws_dash.cell(row=r, column=c).border = border_cell

    # Summary Tables Section in Dashboard
    ws_dash["B12"] = "ملخص موقف السيولة النقدية"
    ws_dash["B12"].font = Font(name=font_family, size=11, bold=True, color="1B365D")
    
    cash_headers = ["الحساب", "الرصيد الحالي", "النسبة من السيولة"]
    for i, h in enumerate(cash_headers, start=2):
        c = ws_dash.cell(row=13, column=i, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    ws_dash["B14"] = "الخزينة (النقدية بالصندوق)"
    ws_dash["C14"] = "=ميزان_المراجعة!H7"
    ws_dash["D14"] = "=C14/$C$16"
    ws_dash["B15"] = "البنوك (الحسابات الجارية)"
    ws_dash["C15"] = "=ميزان_المراجعة!H8"
    ws_dash["D15"] = "=C15/$C$16"
    ws_dash["B16"] = "إجمالي السيولة النقدية"
    ws_dash["C16"] = "=SUM(C14:C15)"
    ws_dash["D16"] = "=SUM(D14:D15)"

    for r in [14, 15]:
        for col in [2, 3, 4]:
            cell = ws_dash.cell(row=r, column=col)
            cell.font = data_font
            cell.border = border_cell
            if col == 3: cell.number_format = num_fmt
            if col == 4: cell.number_format = pct_fmt
    for col in [2, 3, 4]:
        cell = ws_dash.cell(row=16, column=col)
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border_total
        if col == 3: cell.number_format = num_fmt
        if col == 4: cell.number_format = pct_fmt

    # Financial Performance Indicators in Dashboard
    ws_dash["F12"] = "مؤشرات الربحية والهوامش المالية"
    ws_dash["F12"].font = Font(name=font_family, size=11, bold=True, color="1B365D")
    
    ratios = [
        ("هامش مجمل الربح (Gross Margin %)", "=قائمة_الدخل!D13/قائمة_الدخل!D7"),
        ("هامش الربح التشغيلي (Operating Margin %)", "=قائمة_الدخل!D20/قائمة_الدخل!D7"),
        ("هامش صافي الربح (Net Profit Margin %)", "=قائمة_الدخل!D25/قائمة_الدخل!D7"),
        ("العائد على حقوق الملكية (ROE %)", "=قائمة_الدخل!D25/المركز_المالي!D20"),
    ]
    ws_dash.cell(row=13, column=6, value="المؤشر المالي").font = tbl_header_font
    ws_dash.cell(row=13, column=6).fill = slate_header
    ws_dash.cell(row=13, column=6).border = border_cell
    ws_dash.cell(row=13, column=7, value="النسبة").font = tbl_header_font
    ws_dash.cell(row=13, column=7).fill = slate_header
    ws_dash.cell(row=13, column=7).border = border_cell

    for idx, (label, form) in enumerate(ratios, start=14):
        c1 = ws_dash.cell(row=idx, column=6, value=label)
        c2 = ws_dash.cell(row=idx, column=7, value=form)
        c1.font = data_font; c1.border = border_cell
        c2.font = data_bold; c2.border = border_cell
        c2.number_format = pct_fmt
        c2.alignment = align_center

    # ==========================================
    # 2. دليل الحسابات الشجري (Chart of Accounts - COA)
    # ==========================================
    ws_coa = wb.create_sheet("دليل_الحسابات")
    style_sheet(ws_coa)

    ws_coa.merge_cells("A1:H1")
    ws_coa["A1"] = "شجرة ودليل الحسابات المالي الموحد (Chart of Accounts)"
    ws_coa["A1"].font = title_font
    ws_coa["A1"].fill = navy_dark
    ws_coa["A1"].alignment = align_center
    ws_coa.row_dimensions[1].height = 35

    coa_headers = ["كود الحساب", "اسم الحساب", "الحساب الرئيسي", "المستوى", "طبيعة الحساب", "القائمة المالية", "الرصيد الافتتاحي مدين", "الرصيد الافتتاحي دائن"]
    for col_idx, h in enumerate(coa_headers, start=1):
        c = ws_coa.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell
    ws_coa.row_dimensions[2].height = 25

    coa_data = [
        ("1110", "الأصول الثابتة - سيارات", "الأصول غير المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1120", "الأصول الثابتة - أثاث ومعدات مكاتب", "الأصول غير المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1190", "مجمع إهلاك الأصول الثابتة", "الأصول غير المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("1210", "الخزينة (النقدية بالصندوق)", "الأصول المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1220", "البنوك (الحسابات الجارية)", "الأصول المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1230", "العملاء (المدينون التجاريون)", "الأصول المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1240", "المخزون (بضاعة آخر المدة)", "الأصول المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("1250", "أرصدة مدينة أخرى", "الأصول المتداولة", 3, "مدين", "المركز المالي", 0, 0),
        ("2110", "الموردون (الدائنون التجاريون)", "الالتزامات المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("2120", "مخصص ضريبة الدخل المستحقة", "الالتزامات المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("2130", "ضريبة القيمة المضافة (VAT)", "الالتزامات المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("2140", "التأمينات الاجتماعية", "الالتزامات المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("2150", "أرصدة دائنة أخرى", "الالتزامات المتداولة", 3, "دائن", "المركز المالي", 0, 0),
        ("3110", "رأس المال المدفوع", "حقوق الملكية", 3, "دائن", "المركز المالي", 0, 0),
        ("3120", "الأرباح المرحلة", "حقوق الملكية", 3, "دائن", "المركز المالي", 0, 0),
        ("3130", "جاري الشركاء", "حقوق الملكية", 3, "مدين/دائن", "المركز المالي", 0, 0),
        ("4110", "المبيعات", "الإيرادات", 3, "دائن", "قائمة الدخل", 0, 0),
        ("4210", "إيرادات خدمات وأنشطة أخرى", "الإيرادات", 3, "دائن", "قائمة الدخل", 0, 0),
        ("5110", "المشتريات (تكلفة النشاط)", "تكلفة النشاط", 3, "مدين", "قائمة الدخل", 0, 0),
        ("5210", "المصروفات - مرتبات وأجور", "المصروفات التشغيلية والإدارية", 3, "مدين", "قائمة الدخل", 0, 0),
        ("5220", "المصروفات - إيجار مقر الشركة", "المصروفات التشغيلية والإدارية", 3, "مدين", "قائمة الدخل", 0, 0),
        ("5230", "المصروفات - كهرباء ومياه ومرافق", "المصروفات التشغيلية والإدارية", 3, "مدين", "قائمة الدخل", 0, 0),
        ("5240", "مصروف إهلاك الأصول الثابتة", "المصروفات التشغيلية والإدارية", 3, "مدين", "قائمة الدخل", 0, 0),
        ("5250", "مصروفات إدارية وعمومية أخرى", "المصروفات التشغيلية والإدارية", 3, "مدين", "قائمة الدخل", 0, 0),
    ]

    for row_idx, r_data in enumerate(coa_data, start=3):
        for col_idx, val in enumerate(r_data, start=1):
            cell = ws_coa.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [1, 4, 5, 6]:
                cell.alignment = align_center
            elif col_idx in [7, 8]:
                cell.number_format = num_fmt
                cell.alignment = align_right

    # ==========================================
    # 3. اليومية العامة وقاعدة بيانات الحركات (General_Ledger)
    # ==========================================
    ws_gl = wb.create_sheet("اليومية_العامة")
    style_sheet(ws_gl)

    ws_gl.merge_cells("A1:L1")
    ws_gl["A1"] = "سجل اليومية العامة وقاعدة الحركات المحاسبية الموحدة (General Journal Transactions)"
    ws_gl["A1"].font = title_font
    ws_gl["A1"].fill = navy_dark
    ws_gl["A1"].alignment = align_center
    ws_gl.row_dimensions[1].height = 35

    gl_headers = [
        "مسلسل", "رقم القيد", "التاريخ", "الشهر", "كود الحساب", 
        "اسم الحساب", "الطرف / مركز التكلفة", "البيان والشرح التفصيلي", 
        "مدين", "دائن", "رقم المستند", "حالة القيد"
    ]
    for col_idx, h in enumerate(gl_headers, start=1):
        c = ws_gl.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell
    ws_gl.row_dimensions[2].height = 25

    raw_journal = [
        # Entry 1: Capital deposit
        (1, "2016-01-01", 1, "1210", "الخزينة (النقدية بالصندوق)", "المركز الرئيسي", "إيداع حصة نقدية بالخزينة من رأس المال", 250000, 0, "قيد-1"),
        (1, "2016-01-01", 1, "1220", "البنوك (الحسابات الجارية)", "بنك مصر", "إيداع حصة نقدية بالبنك من رأس المال", 500000, 0, "قيد-1"),
        (1, "2016-01-01", 1, "1110", "الأصول الثابتة - سيارات", "سيارات الشركة", "حصة عينية سيارة لنقل البضائع", 120000, 0, "قيد-1"),
        (1, "2016-01-01", 1, "5110", "المشتريات (تكلفة النشاط)", "بضاعة تأسيس", "حصة عينية بضاعة ومواد خام", 130000, 0, "قيد-1"),
        (1, "2016-01-01", 1, "3110", "رأس المال المدفوع", "المساهمون", "إثبات تأسيس الشركة برأس مال مليون جنيه", 0, 1000000, "قيد-1"),

        # Entry 2: Purchase from El-Hamd
        (2, "2016-01-25", 1, "5110", "المشتريات (تكلفة النشاط)", "شركة الحمد", "شراء بضاعة من شركة الحمد", 250000, 0, "فاتورة-101"),
        (2, "2016-01-25", 1, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "سداد نصف قيمة المشتريات نقداً", 0, 125000, "سند صرف-1"),
        (2, "2016-01-25", 1, "2110", "الموردون (الدائنون التجاريون)", "شركة الحمد", "المستحق بالأجل لشركة الحمد", 0, 125000, "فاتورة-101"),

        # Entry 3: Sales to El-Hoda
        (3, "2016-02-07", 2, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل نقدي جزء من قيمة مبيعات بضاعة", 300000, 0, "سند قبض-1"),
        (3, "2016-02-07", 2, "1230", "العملاء (المدينون التجاريون)", "شركة الهدى", "المستحق بالأجل على شركة الهدى", 50000, 0, "فاتورة مبيعات-1"),
        (3, "2016-02-07", 2, "4110", "المبيعات", "شركة الهدى", "إثبات مبيعات بضاعة لشركة الهدى", 0, 350000, "فاتورة مبيعات-1"),

        # Entry 4: Purchase delivery car by bank
        (4, "2016-02-28", 2, "1110", "الأصول الثابتة - سيارات", "إدارة الحركة", "شراء سيارة نقل بضائع للشركة بشيك", 120000, 0, "شيك-5501"),
        (4, "2016-02-28", 2, "1220", "البنوك (الحسابات الجارية)", "بنك مصر", "سحب شيك شراء سيارة نقل", 0, 120000, "شيك-5501"),

        # Entry 5: Salaries Jan & Feb
        (5, "2016-03-01", 3, "5210", "المصروفات - مرتبات وأجور", "الإدارة والموظفين", "سداد مرتبات شهر يناير وفبراير نقداً", 60000, 0, "سند صرف-2"),
        (5, "2016-03-01", 3, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف مرتبات الموظفين", 0, 60000, "سند صرف-2"),

        # Entry 6: Services revenue cash
        (6, "2016-03-15", 3, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل إيراد تقديم خدمات استشارية وتسويقية", 90000, 0, "سند قبض-2"),
        (6, "2016-03-15", 3, "4210", "إيرادات خدمات وأنشطة أخرى", "إيرادات خدمات", "إثبات إيراد خدمات مقدمة للغير نقداً", 0, 90000, "سند قبض-2"),

        # Entry 7: Settle supplier El-Hamd
        (7, "2016-04-01", 4, "2110", "الموردون (الدائنون التجاريون)", "شركة الحمد", "سداد المستحق لشركة الحمد نقداً", 125000, 0, "سند صرف-3"),
        (7, "2016-04-01", 4, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف سداد مستحقات شركة الحمد", 0, 125000, "سند صرف-3"),

        # Entry 8: Collect from El-Hoda
        (8, "2016-04-30", 4, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل باقي المستحق على شركة الهدى نقداً", 50000, 0, "سند قبض-3"),
        (8, "2016-04-30", 4, "1230", "العملاء (المدينون التجاريون)", "شركة الهدى", "تسوية رصيد حساب شركة الهدى", 0, 50000, "سند قبض-3"),

        # Entry 9: Utilities (Electricity & Water)
        (9, "2016-05-25", 5, "5230", "المصروفات - كهرباء ومياه ومرافق", "المقر الإداري", "سداد فواتير كهرباء ومياه وانترنت", 5000, 0, "إيصال سداد"),
        (9, "2016-05-25", 5, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف مصاريف مرافق وكهرباء", 0, 5000, "سند صرف-4"),

        # Entry 10: Rent payment
        (10, "2016-06-30", 6, "5220", "المصروفات - إيجار مقر الشركة", "المقر الرئيسي", "سداد إيجار مقر الشركة نقداً", 24000, 0, "إيصال إيجار"),
        (10, "2016-06-30", 6, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف إيجار المقر", 0, 24000, "سند صرف-5"),

        # Entry 11: Cash sales
        (11, "2016-07-12", 7, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل مبيعات بضاعة نقداً بالخزينة", 95000, 0, "فاتورة مبيعات-2"),
        (11, "2016-07-12", 7, "4110", "المبيعات", "مبيعات نقدية", "إثبات مبيعات تجارية نقدية", 0, 95000, "فاتورة مبيعات-2"),

        # Entry 12: Cash purchase
        (12, "2016-08-20", 8, "5110", "المشتريات (تكلفة النشاط)", "مشتريات نقدية", "شراء بضاعة نقداً من السوق المحلي", 30000, 0, "فاتورة شراء"),
        (12, "2016-08-20", 8, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "سداد قيمة مشتريات نقداً", 0, 30000, "سند صرف-6"),

        # Entry 13: Partner withdrawal
        (13, "2016-09-14", 9, "3130", "جاري الشركاء", "الشريك محمود خليفة", "مسحوبات نقدية للشريك محمود خليفة", 40000, 0, "سند صرف-7"),
        (13, "2016-09-14", 9, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف مسحوبات الشريك نقداً", 0, 40000, "سند صرف-7"),

        # Entry 14: Credit purchase from El-Amal
        (14, "2016-10-30", 10, "5110", "المشتريات (تكلفة النشاط)", "شركة الأمل", "شراء بضاعة بالأجل من شركة الأمل", 50000, 0, "فاتورة-204"),
        (14, "2016-10-30", 10, "2110", "الموردون (الدائنون التجاريون)", "شركة الأمل", "المستحق بالأجل لشركة الأمل", 0, 50000, "فاتورة-204"),

        # Entry 15: Salaries payment
        (15, "2016-11-01", 11, "5210", "المصروفات - مرتبات وأجور", "الموظفين", "سداد مرتبات الموظفين نقداً", 60000, 0, "سند صرف-8"),
        (15, "2016-11-01", 11, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "صرف رواتب الموظفين", 0, 60000, "سند صرف-8"),

        # Entry 16: Services revenue cash
        (16, "2016-11-25", 11, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل إيراد خدمات نقداً", 60000, 0, "سند قبض-4"),
        (16, "2016-11-25", 11, "4210", "إيرادات خدمات وأنشطة أخرى", "إيرادات خدمات", "إثبات إيراد خدمات مقدمة للعملاء", 0, 60000, "سند قبض-4"),

        # Entry 17: Credit sales to El-Nour
        (17, "2016-12-01", 12, "1230", "العملاء (المدينون التجاريون)", "شركة النور", "مبيعات بضاعة بالأجل لشركة النور", 12000, 0, "فاتورة مبيعات-3"),
        (17, "2016-12-01", 12, "4110", "المبيعات", "شركة النور", "إثبات مبيعات بضاعة بالأجل", 0, 12000, "فاتورة مبيعات-3"),

        # Entry 18: Treasury deposit to bank
        (18, "2016-12-16", 12, "1220", "البنوك (الحسابات الجارية)", "بنك مصر", "إيداع نقدي بالحساب الجاري بالبنك", 50000, 0, "إيصال إيداع-902"),
        (18, "2016-12-16", 12, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحويل نقدية من الخزينة للبنك", 0, 50000, "إذن توريد"),

        # Entry 19: Office furniture purchased by bank
        (19, "2016-12-20", 12, "1120", "الأصول الثابتة - أثاث ومعدات مكاتب", "الفرع الثاني", "شراء أثاث مكتبي وتجهيزات للفرع الثاني بشيك", 120000, 0, "شيك-5502"),
        (19, "2016-12-20", 12, "1220", "البنوك (الحسابات الجارية)", "بنك مصر", "سداد قيمة أثاث مكتبي بشيك", 0, 120000, "شيك-5502"),

        # Entry 20: Half-cash half-credit sales
        (20, "2016-12-30", 12, "1210", "الخزينة (النقدية بالصندوق)", "الخزينة", "تحصيل نصف قيمة المبيعات نقداً", 90000, 0, "سند قبض-5"),
        (20, "2016-12-30", 12, "1230", "العملاء (المدينون التجاريون)", "شركة السلام", "المستحق بالأجل على شركة السلام", 90000, 0, "فاتورة مبيعات-4"),
        (20, "2016-12-30", 12, "4110", "المبيعات", "شركة السلام", "إثبات مبيعات بضاعة نصف نقدي ونصف آجل", 0, 180000, "فاتورة مبيعات-4"),

        # Entry 21: Accurate Depreciation adjusting entry
        (21, "2016-12-31", 12, "5240", "مصروف إهلاك الأصول الثابتة", "تسويات جردية", "إثبات قسط إهلاك الأصول الثابتة السنوي الدقيق", 34250, 0, "تسوية-1"),
        (21, "2016-12-31", 12, "1190", "مجمع إهلاك الأصول الثابتة", "تسويات جردية", "إثبات مجمع إهلاك الأصول الثابتة السنوي", 0, 34250, "تسوية-1"),

        # Entry 22: Ending Inventory adjusting entry
        # Debit: Inventory (1240) in Balance Sheet
        # Credit: Closing Inventory (Revenues/Income summary) or we debit inventory and credit retained earnings/income summary
        # In a standard periodic journal entry, ending inventory is debited to 1240 and credited to Income Statement (or cost of sales offset)
        (22, "2016-12-31", 12, "1240", "المخزون (بضاعة آخر المدة)", "تسويات جردية", "إثبات مخزون بضاعة آخر المدة الفعلي بالدفاتر", 9000, 0, "محضر جرد-1"),
        (22, "2016-12-31", 12, "4210", "إيرادات خدمات وأنشطة أخرى", "تسويات جردية", "إثبات قيمة بضاعة آخر المدة كإيراد تخفيض لتكلفة المبيعات", 0, 0, "محضر جرد-1"), 
        # Note: To avoid double counting, in COGS we compute: Beginning Inv + Purchases - Ending Inv.
        # So in the journal, we directly debit Inventory 1240 and credit Capital/Inventory Adjustments, OR we reflect it in COGS.
        # Here: we offset it against Purchases directly:
    ]

    # Let's adjust Entry 22 so Purchases reflects 460,000, and ending inventory 9,000 is booked against an inventory change account, OR:
    # Let's see: Purchases in journal was 130k + 250k + 30k + 50k = 460,000.
    # If Entry 22 is:
    # Dr: المخزون (1240) 9000
    # Cr: أرصدة دائنة أخرى / وسيط مخزون 9000
    # OR: Dr المخزون 9000 / Cr المشتريات 9000 -> then Purchases in TB is 451,000.
    # If Purchases in TB is 451,000, then in Income Statement:
    # COGS = Purchases (451,000) WITHOUT subtracting ending inventory again!
    # Let's make COGS in Income Statement = Purchases from TB (which is 451,000) if it's already net of ending inventory, OR:
    # Keep Purchases = 460,000 (no credit to purchases), and credit Ending Inventory Account (3120 or 4210).
    # The cleanest standard approach:
    # Dr: 1240 المخزون = 9,000
    # Cr: 1250 / 2150 or direct equity offset.
    # Actually, let's keep Entry 22 as:
    # Dr: المخزون 1240: 9,000
    # Cr: المشتريات 5110: 9,000
    # Then in Income Statement:
    # Row 10: المشتريات = 460,000 (we can calculate original purchases = 460,000, less ending inventory 9,000 = 451,000).
    # That way both the detailed line items in Income Statement make sense AND total COGS = 451,000!

    raw_journal[-2] = (22, "2016-12-31", 12, "1240", "المخزون (بضاعة آخر المدة)", "تسويات جردية", "إثبات مخزون بضاعة آخر المدة الفعلي بالدفاتر", 9000, 0, "محضر جرد-1")
    raw_journal[-1] = (22, "2016-12-31", 12, "5110", "المشتريات (تكلفة النشاط)", "تسويات جردية", "تخفيض المشتريات بمخزون آخر المدة للوصول لتكلفة البضاعة المباعة", 0, 9000, "محضر جرد-1")

    # Entry 23: Income Tax Provision
    # Net profit before tax = 152,750
    # Tax @ 22.5% = 34,368.75
    raw_journal.append((23, "2016-12-31", 12, "5250", "مصروفات إدارية وعمومية أخرى", "تسويات جردية", "إثبات عبء مخصص ضريبة الدخل السنوية (22.5%)", 34368.75, 0, "إقرار ضريبي"))
    raw_journal.append((23, "2016-12-31", 12, "2120", "مخصص ضريبة الدخل المستحقة", "مصلحة الضرائب", "التزام ضريبة الدخل المستحقة لمصلحة الضرائب", 0, 34368.75, "إقرار ضريبي"))

    for row_idx, r_data in enumerate(raw_journal, start=3):
        ws_gl.cell(row=row_idx, column=1, value=row_idx-2).alignment = align_center
        for col_idx, val in enumerate(r_data, start=2):
            cell = ws_gl.cell(row=row_idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [2, 3, 4, 5, 11]:
                cell.alignment = align_center
            elif col_idx in [9, 10]:
                cell.number_format = num_fmt
                cell.alignment = align_right

        ws_gl.cell(row=row_idx, column=12, value=f'=IF(SUMIFS($I$3:$I$100, $B$3:$B$100, B{row_idx})=SUMIFS($J$3:$J$100, $B$3:$B$100, B{row_idx}), "متزن", "غير متزن")')
        ws_gl.cell(row=row_idx, column=12).font = success_font
        ws_gl.cell(row=row_idx, column=12).alignment = align_center
        ws_gl.cell(row=row_idx, column=12).border = border_cell

    last_gl_row = len(raw_journal) + 2
    ws_gl.merge_cells(f"A{last_gl_row+1}:H{last_gl_row+1}")
    t_label = ws_gl.cell(row=last_gl_row+1, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام")
    t_label.font = total_font; t_label.alignment = align_center; t_label.fill = total_fill

    t_dr = ws_gl.cell(row=last_gl_row+1, column=9, value=f"=SUM(I3:I{last_gl_row})")
    t_dr.font = total_font; t_dr.fill = total_fill; t_dr.number_format = num_fmt; t_dr.border = border_total

    t_cr = ws_gl.cell(row=last_gl_row+1, column=10, value=f"=SUM(J3:J{last_gl_row})")
    t_cr.font = total_font; t_cr.fill = total_fill; t_cr.number_format = num_fmt; t_cr.border = border_total

    t_chk = ws_gl.cell(row=last_gl_row+1, column=12, value=f'=IF(ROUND(I{last_gl_row+1},2)=ROUND(J{last_gl_row+1},2), "اليومية متزنة تماماً", "يوجد خلل في التوازن")')
    t_chk.font = success_font; t_chk.fill = success_fill; t_chk.alignment = align_center; t_chk.border = border_total

    for c in range(1, 13):
        ws_gl.cell(row=last_gl_row+1, column=c).border = border_total

    # ==========================================
    # 4. ميزان المراجعة الشامل (Trial_Balance)
    # ==========================================
    ws_tb = wb.create_sheet("ميزان_المراجعة")
    style_sheet(ws_tb)

    ws_tb.merge_cells("A1:I1")
    ws_tb["A1"] = "ميزان المراجعة الشامل بالمجاميع والأرصدة (Trial Balance)"
    ws_tb["A1"].font = title_font
    ws_tb["A1"].fill = navy_dark
    ws_tb["A1"].alignment = align_center
    ws_tb.row_dimensions[1].height = 35

    ws_tb.merge_cells("A2:A3"); ws_tb["A2"] = "كود الحساب"
    ws_tb.merge_cells("B2:B3"); ws_tb["B2"] = "اسم الحساب"
    ws_tb.merge_cells("C2:C3"); ws_tb["C2"] = "طبيعة الحساب"

    ws_tb.merge_cells("D2:E2"); ws_tb["D2"] = "الأرصدة الافتتاحية"
    ws_tb["D3"] = "مدين"; ws_tb["E3"] = "دائن"

    ws_tb.merge_cells("F2:G2"); ws_tb["F2"] = "حركات الفترة (اليومية العامة)"
    ws_tb["F3"] = "مدين"; ws_tb["G3"] = "دائن"

    ws_tb.merge_cells("H2:I2"); ws_tb["H2"] = "الأرصدة الختامية"
    ws_tb["H3"] = "مدين"; ws_tb["I3"] = "دائن"

    for r in [2, 3]:
        for c in range(1, 10):
            cell = ws_tb.cell(row=r, column=c)
            cell.font = tbl_header_font
            cell.fill = slate_header
            cell.alignment = align_center
            cell.border = border_cell

    for idx, acc in enumerate(coa_data, start=4):
        code, name, parent, level, nature, stmt, op_dr, op_cr = acc
        ws_tb.cell(row=idx, column=1, value=code).alignment = align_center
        ws_tb.cell(row=idx, column=2, value=name)
        ws_tb.cell(row=idx, column=3, value=nature).alignment = align_center
        ws_tb.cell(row=idx, column=4, value=op_dr).number_format = num_fmt
        ws_tb.cell(row=idx, column=5, value=op_cr).number_format = num_fmt
        
        ws_tb.cell(row=idx, column=6, value=f'=SUMIFS(اليومية_العامة!$I$3:$I$100, اليومية_العامة!$E$3:$E$100, A{idx})').number_format = num_fmt
        ws_tb.cell(row=idx, column=7, value=f'=SUMIFS(اليومية_العامة!$J$3:$J$100, اليومية_العامة!$E$3:$E$100, A{idx})').number_format = num_fmt

        ws_tb.cell(row=idx, column=8, value=f'=IF(ROUND((D{idx}+F{idx}-E{idx}-G{idx}),2)>0, (D{idx}+F{idx}-E{idx}-G{idx}), 0)').number_format = num_fmt
        ws_tb.cell(row=idx, column=9, value=f'=IF(ROUND((E{idx}+G{idx}-D{idx}-F{idx}),2)>0, (E{idx}+G{idx}-D{idx}-F{idx}), 0)').number_format = num_fmt

        for c in range(1, 10):
            ws_tb.cell(row=idx, column=c).border = border_cell
            ws_tb.cell(row=idx, column=c).font = data_font

    tb_last = len(coa_data) + 3
    ws_tb.merge_cells(f"A{tb_last+1}:C{tb_last+1}")
    ws_tb.cell(row=tb_last+1, column=1, value="الإجمـــــــــــــــــــــــــــــــــالي العــــــــــــــــــــام").font = total_font
    ws_tb.cell(row=tb_last+1, column=1).alignment = align_center
    ws_tb.cell(row=tb_last+1, column=1).fill = total_fill

    for c in range(4, 10):
        col_let = get_column_letter(c)
        cell = ws_tb.cell(row=tb_last+1, column=c, value=f'=SUM({col_let}4:{col_let}{tb_last})')
        cell.font = total_font; cell.fill = total_fill; cell.number_format = num_fmt; cell.border = border_total

    # ==========================================
    # 5. قائمة الدخل (Income_Statement)
    # ==========================================
    ws_is = wb.create_sheet("قائمة_الدخل")
    style_sheet(ws_is)

    ws_is.merge_cells("A1:D1")
    ws_is["A1"] = "قائمة الدخل الشاملة عن السنة المالية المنتهية في 31 ديسمبر 2016"
    ws_is["A1"].font = title_font
    ws_is["A1"].fill = navy_dark
    ws_is["A1"].alignment = align_center
    ws_is.row_dimensions[1].height = 35

    is_headers = ["كود الحساب", "البيـــــــــــــــــــــــــــــــــان", "جزئي (ج.م)", "كلي (ج.م)"]
    for col_idx, h in enumerate(is_headers, start=1):
        c = ws_is.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    is_structure = [
        (3, "", "الإيرادات التشغيلية:", "", "", False, True),
        (4, "4110", "إجمالي إيرادات المبيعات", "=ميزان_المراجعة!I20", "", False, False),
        (5, "", "يطرح: مردودات ومسموحات المبيعات", 0, "", False, False),
        (6, "", "يطرح: الخصم المسموح به", 0, "", False, False),
        (7, "", "صافي إيرادات المبيعات", "", "=C4-C5-C6", True, False),
        
        (8, "", "تكلفة المبيعات:", "", "", False, True),
        (9, "", "مخزون أول المدة", 0, "", False, False),
        (10, "5110", "إجمالي المشتريات خلال الفترة", "=ميزان_المراجعة!F22", "", False, False),
        (11, "1240", "يطرح: مخزون آخر المدة الفعلي", "=ميزان_المراجعة!H10", "", False, False),
        (12, "", "تكلفة البضاعة المباعة (COGS)", "", "=C9+C10-C11", True, False),
        (13, "", "مجمل الربح (Gross Profit)", "", "=D7-D12", True, False),

        (14, "", "يطرح: المصروفات التشغيلية والإدارية:", "", "", False, True),
        (15, "5210", "مرتبات وأجور إدارية", "=ميزان_المراجعة!H23", "", False, False),
        (16, "5220", "إيجار مقر الشركة", "=ميزان_المراجعة!H24", "", False, False),
        (17, "5230", "كهرباء ومياه ومرافق", "=ميزان_المراجعة!H25", "", False, False),
        (18, "5240", "مصروف إهلاك الأصول الثابتة", "=ميزان_المراجعة!H26", "", False, False),
        (19, "", "إجمالي المصروفات الإدارية والعمومية", "", "=SUM(C15:C18)", True, False),
        (20, "", "صافي الربح التشغيلي (EBIT)", "", "=D13-D19", True, False),

        (21, "", "الإيرادات والمصروفات الأخرى:", "", "", False, True),
        (22, "4210", "إيرادات خدمات وأنشطة أخرى", "=ميزان_المراجعة!I21", "", False, False),
        (23, "", "صافي الربح قبل الضريبة (EBT)", "", "=D20+C22", True, False),
        (24, "2120", "يطرح: ضريبة الدخل المستحقة (22.5%)", "", "=D23*0.225", False, False),
        (25, "", "صافي الربح بعد الضريبة القابل للتوزيع (Net Income)", "", "=D23-D24", True, False),
    ]

    for r_idx, code, label, part, full, is_tot, is_head in is_structure:
        ws_is.cell(row=r_idx, column=1, value=code).alignment = align_center
        ws_is.cell(row=r_idx, column=2, value=label)
        
        c_part = ws_is.cell(row=r_idx, column=3, value=part)
        c_full = ws_is.cell(row=r_idx, column=4, value=full)

        c_part.number_format = num_fmt
        c_full.number_format = num_fmt

        for c in range(1, 5):
            cell = ws_is.cell(row=r_idx, column=c)
            cell.border = border_cell
            if is_head:
                cell.font = data_bold
                cell.fill = subtotal_fill
            elif is_tot:
                cell.font = total_font
                cell.fill = total_fill
                if "صافي الربح بعد الضريبة" in label:
                    cell.fill = gold_fill
                    cell.font = Font(name=font_family, size=11, bold=True, color="1B365D")
                    cell.border = border_total
            else:
                cell.font = data_font

    # ==========================================
    # 6. قائمة المركز المالي (Balance_Sheet)
    # ==========================================
    ws_bs = wb.create_sheet("المركز_المالي")
    style_sheet(ws_bs)

    ws_bs.merge_cells("A1:D1")
    ws_bs["A1"] = "قائمة المركز المالي (الميزانية العمومية) في 31 ديسمبر 2016"
    ws_bs["A1"].font = title_font
    ws_bs["A1"].fill = navy_dark
    ws_bs["A1"].alignment = align_center
    ws_bs.row_dimensions[1].height = 35

    bs_headers = ["إيضاح", "الأصـــــــــــــــــــــــــــــــــول", "جزئي (ج.م)", "كلي (ج.م)"]
    for col_idx, h in enumerate(bs_headers, start=1):
        c = ws_bs.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    bs_structure = [
        (3, "", "الأصول طويلة الأجل (غير المتداولة):", "", "", False, True),
        (4, "1/4", "الأصول الثابتة الإجمالية (سيارات وأثاث)", "=ميزان_المراجعة!H4+ميزان_المراجعة!H5", "", False, False),
        (5, "2/4", "يطرح: مجمع إهلاك الأصول الثابتة", "=ميزان_المراجعة!I6", "", False, False),
        (6, "", "صافي الأصول الثابتة", "", "=C4-C5", True, False),
        (7, "", "إجمالي الأصول طويلة الأجل", "", "=D6", True, False),
        
        (8, "", "الأصول المتداولة:", "", "", False, True),
        (9, "1/5", "النقدية وما في حكمها (خزينة وبنوك)", "=ميزان_المراجعة!H7+ميزان_المراجعة!H8", "", False, False),
        (10, "2/5", "العملاء (المدينون التجاريون)", "=ميزان_المراجعة!H9", "", False, False),
        (11, "3/5", "المخزون (بضاعة آخر المدة)", "=ميزان_المراجعة!H10", "", False, False),
        (12, "4/5", "أرصدة مدينة أخرى", "=ميزان_المراجعة!H11", "", False, False),
        (13, "", "إجمالي الأصول المتداولة", "", "=SUM(C9:C12)", True, False),
        (14, "", "إجمـــــــــــــــــــــــــــــــــالي الأصـــــــــــــــــــــول", "", "=D7+D13", True, False),
        
        # Equity & Liabilities
        (15, "", "حقوق الملكية والالتزامات:", "", "", False, True),
        (16, "", "حقوق الملكية:", "", "", False, True),
        (17, "1/6", "رأس المال المدفوع", "=ميزان_المراجعة!I17", "", False, False),
        (18, "2/6", "أرباح العام الصافية بعد الضريبة", "=قائمة_الدخل!D25", "", False, False),
        (19, "3/6", "جاري الشركاء (مسحوبات الشريك محمود)", "=-(ميزان_المراجعة!H19-ميزان_المراجعة!I19)", "", False, False),
        (20, "", "إجمالي حقوق الملكية", "", "=SUM(C17:C19)", True, False),
        
        (21, "", "الالتزامات المتداولة:", "", "", False, True),
        (22, "1/7", "الموردون (الدائنون التجاريون)", "=ميزان_المراجعة!I12", "", False, False),
        (23, "2/7", "مخصص ضريبة الدخل المستحقة", "=ميزان_المراجعة!I13", "", False, False),
        (24, "3/7", "أرصدة دائنة أخرى وتأمينات", "=ميزان_المراجعة!I14+ميزان_المراجعة!I15+ميزان_المراجعة!I16", "", False, False),
        (25, "", "إجمالي الالتزامات المتداولة", "", "=SUM(C22:C24)", True, False),
        (26, "", "إجمـــــالي حقوق الملكية والالتزامات", "", "=D20+D25", True, False),
        (27, "", "فحص توازن الميزانية العمومية", "", '=IF(ROUND(D14,2)=ROUND(D26,2), "الميزانية متزنة تماماً 100%", "يوجد فرق: " & (D14-D26))', True, False),
    ]

    for r_idx, note, label, part, full, is_tot, is_head in bs_structure:
        ws_bs.cell(row=r_idx, column=1, value=note).alignment = align_center
        ws_bs.cell(row=r_idx, column=2, value=label)
        
        c_part = ws_bs.cell(row=r_idx, column=3, value=part)
        c_full = ws_bs.cell(row=r_idx, column=4, value=full)

        if str(part).startswith("="): c_part.number_format = num_fmt
        if str(full).startswith("="): c_full.number_format = num_fmt

        for c in range(1, 5):
            cell = ws_bs.cell(row=r_idx, column=c)
            cell.border = border_cell
            if is_head:
                cell.font = data_bold
                cell.fill = subtotal_fill
            elif is_tot:
                cell.font = total_font
                cell.fill = total_fill
                if "فحص توازن" in label:
                    cell.font = success_font
                    cell.fill = success_fill
                    cell.border = border_total
                elif "إجمـــــالي" in label:
                    cell.font = Font(name=font_family, size=11, bold=True, color="1B365D")
                    cell.border = border_total
            else:
                cell.font = data_font

    # ==========================================
    # 7. قائمة التدفقات النقدية (Cash_Flow)
    # ==========================================
    ws_cf = wb.create_sheet("التدفقات_النقدية")
    style_sheet(ws_cf)

    ws_cf.merge_cells("A1:C1")
    ws_cf["A1"] = "قائمة التدفقات النقدية (الطريقة غير المباشرة) للسنة المالية 2016"
    ws_cf["A1"].font = title_font
    ws_cf["A1"].fill = navy_dark
    ws_cf["A1"].alignment = align_center
    ws_cf.row_dimensions[1].height = 35

    cf_headers = ["البنــــــــــــــــــــــــــــــــود", "جزئي (ج.م)", "كلي (ج.م)"]
    for col_idx, h in enumerate(cf_headers, start=1):
        c = ws_cf.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    cf_rows = [
        (3, "أولاً: التدفقات النقدية من الأنشطة التشغيلية:", "", "", True),
        (4, "صافي الربح بعد الضريبة (من قائمة الدخل)", "=قائمة_الدخل!D25", "", False),
        (5, "يضاف: مصروف إهلاك الأصول الثابتة (غير نقدي)", "=قائمة_الدخل!C18", "", False),
        (6, "يضاف: مخصص ضريبة الدخل المستحقة (غير مدفوع بعد)", "=قائمة_الدخل!D24", "", False),
        (7, "يضاف: تسوية بضاعة تأسيس عينية غير نقدية في المشتريات", "=130000", "", False),
        (8, "التغير في رأس المال العامل التشغيلي:", "", "", True),
        (9, "(الزيادة) في أرصدة العملاء والمدينين", "=-المركز_المالي!C10", "", False),
        (10, "(الزيادة) في مخزون بضاعة آخر المدة", "=-المركز_المالي!C11", "", False),
        (11, "الزيادة في أرصدة الموردين والدائنين", "=المركز_المالي!C22", "", False),
        (12, "صافي التدفق النقدي من الأنشطة التشغيلية", "", "=SUM(B4:B7)+SUM(B9:B11)", True),
        
        (13, "ثانياً: التدفقات النقدية من الأنشطة الاستثمارية:", "", "", True),
        (14, "(المدفوعات النقدية) لشراء سيارة نقل بشيك بنكي", "=-120000", "", False),
        (15, "(المدفوعات النقدية) لشراء أثاث ومعدات مكاتب بشيك بنكي", "=-120000", "", False),
        (16, "صافي التدفق النقدي المستخدم في الأنشطة الاستثمارية", "", "=SUM(B14:B15)", True),

        (17, "ثالثاً: التدفقات النقدية من الأنشطة التمويلية:", "", "", True),
        (18, "المقبوض من رأس المال المدفوع نقداً وبالبنك", "=250000+500000", "", False),
        (19, "(مسحوبات الشريك محمود خليفة نقداً)", "=-40000", "", False),
        (20, "صافي التدفق النقدي من الأنشطة التمويلية", "", "=SUM(B18:B19)", True),

        (21, "صافي التغير في النقدية وما في حكمها خلال العام", "", "=C12+C16+C20", True),
        (22, "نقدية وما في حكمها في أول العام (1 يناير 2016)", 0, "", False),
        (23, "نقدية وما في حكمها في نهاية العام (31 ديسمبر 2016)", "", "=C21+B22", True),
        (24, "رصيد النقدية بالخزينة والبنوك الفعلي من الميزانية", "", "=المركز_المالي!C9", True),
        (25, "مطابقة رصيد النقدية والتحقق", "", '=IF(ROUND(C23,2)=ROUND(C24,2), "متطابق تماماً 100%", "يوجد فرق: " & (C23-C24))', True),
    ]

    for r_idx, label, part, full, is_tot in cf_rows:
        ws_cf.cell(row=r_idx, column=1, value=label)
        c_part = ws_cf.cell(row=r_idx, column=2, value=part)
        c_full = ws_cf.cell(row=r_idx, column=3, value=full)

        if str(part).startswith("="): c_part.number_format = num_fmt
        if str(full).startswith("="): c_full.number_format = num_fmt

        for c in range(1, 4):
            cell = ws_cf.cell(row=r_idx, column=c)
            cell.border = border_cell
            if is_tot:
                cell.font = total_font
                cell.fill = total_fill
                if "مطابقة" in label:
                    cell.font = success_font
                    cell.fill = success_fill
                    cell.border = border_total
            else:
                cell.font = data_font

    # ==========================================
    # 8. كشف الحساب التفاعلي الديناميكي (Account_Statement)
    # ==========================================
    ws_stmt = wb.create_sheet("كشف_حساب_ديناميكي")
    style_sheet(ws_stmt)

    ws_stmt.merge_cells("A1:G1")
    ws_stmt["A1"] = "كشف حساب تحليلي تفصيلي ديناميكي (Dynamic Account Statement)"
    ws_stmt["A1"].font = title_font
    ws_stmt["A1"].fill = navy_dark
    ws_stmt["A1"].alignment = align_center
    ws_stmt.row_dimensions[1].height = 35

    ws_stmt["B3"] = "كود الحساب المستعلم عنه:"
    ws_stmt["B3"].font = data_bold
    ws_stmt["C3"] = "1210"
    ws_stmt["C3"].font = Font(name=font_family, size=11, bold=True, color="1B365D")
    ws_stmt["C3"].fill = gold_fill
    ws_stmt["C3"].alignment = align_center
    ws_stmt["C3"].border = border_cell

    ws_stmt["D3"] = "اسم الحساب:"
    ws_stmt["D3"].font = data_bold
    ws_stmt["E3"] = '=VLOOKUP(C3, دليل_الحسابات!A3:B30, 2, FALSE)'
    ws_stmt["E3"].font = Font(name=font_family, size=11, bold=True, color="1B365D")
    ws_stmt["E3"].border = border_cell

    ws_stmt["F3"] = "طبيعة الحساب:"
    ws_stmt["F3"].font = data_bold
    ws_stmt["G3"] = '=VLOOKUP(C3, دليل_الحسابات!A3:E30, 5, FALSE)'
    ws_stmt["G3"].font = data_bold; ws_stmt["G3"].alignment = align_center; ws_stmt["G3"].border = border_cell

    ws_stmt["B5"] = "إجمالي الحركات المدينة"; ws_stmt["B5"].font = kpi_lbl_font; ws_stmt["B5"].fill = subtotal_fill
    ws_stmt["C5"] = '=SUMIFS(اليومية_العامة!$I$3:$I$100, اليومية_العامة!$E$3:$E$100, C3)'
    ws_stmt["C5"].font = data_bold; ws_stmt["C5"].number_format = num_fmt; ws_stmt["C5"].border = border_cell

    ws_stmt["D5"] = "إجمالي الحركات الدائنة"; ws_stmt["D5"].font = kpi_lbl_font; ws_stmt["D5"].fill = subtotal_fill
    ws_stmt["E5"] = '=SUMIFS(اليومية_العامة!$J$3:$J$100, اليومية_العامة!$E$3:$E$100, C3)'
    ws_stmt["E5"].font = data_bold; ws_stmt["E5"].number_format = num_fmt; ws_stmt["E5"].border = border_cell

    ws_stmt["F5"] = "صافي الرصيد الحالي"; ws_stmt["F5"].font = kpi_lbl_font; ws_stmt["F5"].fill = subtotal_fill
    ws_stmt["G5"] = '=C5-E5'
    ws_stmt["G5"].font = Font(name=font_family, size=12, bold=True, color="166534")
    ws_stmt["G5"].fill = success_fill
    ws_stmt["G5"].number_format = num_fmt; ws_stmt["G5"].border = border_cell

    stmt_headers = ["التاريخ", "رقم القيد", "الطرف / مركز التكلفة", "البيان والتفاصيل", "مدين", "دائن", "الرصيد التراكمي"]
    for col_idx, h in enumerate(stmt_headers, start=1):
        c = ws_stmt.cell(row=7, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    ws_stmt.cell(row=8, column=1, value="رصيد أول المدة الافتتاحي").font = data_bold
    ws_stmt.cell(row=8, column=7, value=0).number_format = num_fmt

    # ==========================================
    # 9. أعمار الديون (Aging_Analysis)
    # ==========================================
    ws_aging = wb.create_sheet("أعمار_الديون")
    style_sheet(ws_aging)

    ws_aging.merge_cells("A1:H1")
    ws_aging["A1"] = "تحليل أعمار ديون العملاء والموردين ومخاطر الائتمان (Aging Analysis)"
    ws_aging["A1"].font = title_font
    ws_aging["A1"].fill = navy_dark
    ws_aging["A1"].alignment = align_center
    ws_aging.row_dimensions[1].height = 35

    ws_aging.merge_cells("A3:H3")
    ws_aging["A3"] = "أولاً: تقرير أعمار ديون العملاء (Accounts Receivable Aging)"
    ws_aging["A3"].font = sub_title_font
    ws_aging["A3"].fill = navy_light

    aging_headers = ["اسم العميل", "إجمالي المديونية", "جاري (أقل من 30 يوماً)", "31 - 60 يوماً", "61 - 90 يوماً", "أكثر من 90 يوماً", "تاريخ آخر حركة", "درجة المخاطر"]
    for col_idx, h in enumerate(aging_headers, start=1):
        c = ws_aging.cell(row=4, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    cust_aging_data = [
        ("شركة السلام", 90000, 90000, 0, 0, 0, "2016-12-30", "منخفضة (حديث)"),
        ("شركة النور", 12000, 12000, 0, 0, 0, "2016-12-01", "منخفضة (حديث)"),
        ("شركة الهدى", 0, 0, 0, 0, 0, "2016-04-30", "تم السداد بالكامل"),
    ]

    for idx, c_data in enumerate(cust_aging_data, start=5):
        for col_idx, val in enumerate(c_data, start=1):
            cell = ws_aging.cell(row=idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [2, 3, 4, 5, 6]:
                cell.number_format = num_fmt
                cell.alignment = align_right
            elif col_idx in [7, 8]:
                cell.alignment = align_center

    ws_aging.cell(row=8, column=1, value="إجمالي مديونيات العملاء").font = total_font
    ws_aging.cell(row=8, column=1).fill = total_fill
    for c in range(2, 7):
        col_let = get_column_letter(c)
        cell = ws_aging.cell(row=8, column=c, value=f'=SUM({col_let}5:{col_let}7)')
        cell.font = total_font; cell.fill = total_fill; cell.number_format = num_fmt; cell.border = border_total
    for c in [1, 7, 8]:
        ws_aging.cell(row=8, column=c).border = border_total

    ws_aging.merge_cells("A10:H10")
    ws_aging["A10"] = "ثانياً: تقرير أعمار ديون الموردين (Accounts Payable Aging)"
    ws_aging["A10"].font = sub_title_font
    ws_aging["A10"].fill = navy_light

    for col_idx, h in enumerate(aging_headers[:6] + ["تاريخ الفاتورة", "حالة السداد"], start=1):
        c = ws_aging.cell(row=11, column=col_idx, value=h if col_idx != 1 else "اسم المورد")
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    supp_aging_data = [
        ("شركة الأمل", 50000, 0, 50000, 0, 0, "2016-10-30", "يستحق السداد"),
        ("شركة الحمد", 0, 0, 0, 0, 0, "2016-04-01", "تمت التسوية بالكامل"),
    ]

    for idx, s_data in enumerate(supp_aging_data, start=12):
        for col_idx, val in enumerate(s_data, start=1):
            cell = ws_aging.cell(row=idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [2, 3, 4, 5, 6]:
                cell.number_format = num_fmt
                cell.alignment = align_right
            elif col_idx in [7, 8]:
                cell.alignment = align_center

    ws_aging.cell(row=14, column=1, value="إجمالي مستحقات الموردين").font = total_font
    ws_aging.cell(row=14, column=1).fill = total_fill
    for c in range(2, 7):
        col_let = get_column_letter(c)
        cell = ws_aging.cell(row=14, column=c, value=f'=SUM({col_let}12:{col_let}13)')
        cell.font = total_font; cell.fill = total_fill; cell.number_format = num_fmt; cell.border = border_total
    for c in [1, 7, 8]:
        ws_aging.cell(row=14, column=c).border = border_total

    # ==========================================
    # 10. سجل الأصول الثابتة والإهلاك (Assets_Register)
    # ==========================================
    ws_ast = wb.create_sheet("سجل_الأصول_والإهلاك")
    style_sheet(ws_ast)

    ws_ast.merge_cells("A1:K1")
    ws_ast["A1"] = "سجل الأصول الثابتة ومخصصات الإهلاك الدقيقة للسنة المالية 2016"
    ws_ast["A1"].font = title_font
    ws_ast["A1"].fill = navy_dark
    ws_ast["A1"].alignment = align_center
    ws_ast.row_dimensions[1].height = 35

    ast_headers = [
        "كود الأصل", "اسم الأصل", "التصنيف", "تاريخ الشراء", 
        "تكلفة الشراء", "القيمة التخريدية", "القيمة القابلة للإهلاك", 
        "نسبة الإهلاك السنوية", "شهور الاستخدام", "قسط إهلاك الفترة", "صافي القيمة الدفترية"
    ]
    for col_idx, h in enumerate(ast_headers, start=1):
        c = ws_ast.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    ast_data = [
        ("AST-01", "سيارة نقل بضائع رقم 1", "وسائل نقل وانتقال", "2016-01-01", 120000, 0, "=E3-F3", 0.15, 12, "=G3*H3*(I3/12)", "=E3-J3"),
        ("AST-02", "سيارة نقل بضائع رقم 2", "وسائل نقل وانتقال", "2016-02-28", 120000, 0, "=E4-F4", 0.15, 10, "=G4*H4*(I4/12)", "=E4-J4"),
        ("AST-03", "أثاث وتجهيزات مكتبية - فرع 2", "أثاث ومعدات مكاتب", "2016-12-20", 120000, 0, "=E5-F5", 0.125, 1, "=G5*H5*(I5/12)", "=E5-J5"),
    ]

    for idx, a_row in enumerate(ast_data, start=3):
        for col_idx, val in enumerate(a_row, start=1):
            cell = ws_ast.cell(row=idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [1, 3, 4, 9]:
                cell.alignment = align_center
            elif col_idx in [5, 6, 7, 10, 11]:
                cell.number_format = num_fmt
                cell.alignment = align_right
            elif col_idx == 8:
                cell.number_format = pct_fmt
                cell.alignment = align_center

    ws_ast.merge_cells("A6:D6")
    ws_ast.cell(row=6, column=1, value="الإجمـــــــــــــــــــــــــــــــــــــــــالي").font = total_font
    ws_ast.cell(row=6, column=1).alignment = align_center
    ws_ast.cell(row=6, column=1).fill = total_fill

    for c in [5, 6, 7, 10, 11]:
        col_let = get_column_letter(c)
        cell = ws_ast.cell(row=6, column=c, value=f'=SUM({col_let}3:{col_let}5)')
        cell.font = total_font; cell.fill = total_fill; cell.number_format = num_fmt; cell.border = border_total
    for c in [8, 9]:
        ws_ast.cell(row=6, column=c).border = border_total; ws_ast.cell(row=6, column=c).fill = total_fill

    # ==========================================
    # 11. تحليل المصروفات والربحية (Expenses_Analysis)
    # ==========================================
    ws_exp = wb.create_sheet("تحليل_المصروفات_والربحية")
    style_sheet(ws_exp)

    ws_exp.merge_cells("A1:G1")
    ws_exp["A1"] = "تحليل هيكل المصروفات والربحية والمقارنات النسبية (Expenses Analysis)"
    ws_exp["A1"].font = title_font
    ws_exp["A1"].fill = navy_dark
    ws_exp["A1"].alignment = align_center
    ws_exp.row_dimensions[1].height = 35

    exp_headers = ["بند المصروف", "التصنيف", "المبلغ الفعلي (ج.م)", "الوزن النسبي (%)", "النسبة من المبيعات (%)", "طبيعة السداد", "الأثر المالي"]
    for col_idx, h in enumerate(exp_headers, start=1):
        c = ws_exp.cell(row=2, column=col_idx, value=h)
        c.font = tbl_header_font
        c.fill = slate_header
        c.alignment = align_center
        c.border = border_cell

    exp_data = [
        ("المرتبات والأجور", "إداري وتشغيلي", "=ميزان_المراجعة!H20", "=C3/$C$8", "=C3/قائمة_الدخل!$D$7", "نقدي (خزينة)", "ثابت"),
        ("إيجار مقر الشركة", "إداري وعمومي", "=ميزان_المراجعة!H21", "=C4/$C$8", "=C4/قائمة_الدخل!$D$7", "نقدي (خزينة)", "ثابت"),
        ("كهرباء ومياه ومرافق", "تشغيلي وخدمي", "=ميزان_المراجعة!H22", "=C5/$C$8", "=C5/قائمة_الدخل!$D$7", "نقدي (خزينة)", "شبه متغير"),
        ("مصروف إهلاك الأصول الثابتة", "إداري غير نقدي", "=ميزان_المراجعة!H23", "=C6/$C$8", "=C6/قائمة_الدخل!$D$7", "تسوية دفتري", "ثابت"),
        ("مخصص ضريبة الدخل السنوية", "أعباء ضريبية", "=قائمة_الدخل!$D$24", "=C7/$C$8", "=C7/قائمة_الدخل!$D$7", "تسوية التزام", "مرتبط بالربح"),
    ]

    for idx, e_row in enumerate(exp_data, start=3):
        for col_idx, val in enumerate(e_row, start=1):
            cell = ws_exp.cell(row=idx, column=col_idx, value=val)
            cell.font = data_font
            cell.border = border_cell
            if col_idx in [1, 2, 6, 7]:
                if col_idx in [2, 6, 7]: cell.alignment = align_center
            elif col_idx == 3:
                cell.number_format = num_fmt
                cell.alignment = align_right
            elif col_idx in [4, 5]:
                cell.number_format = pct_fmt
                cell.alignment = align_center

    ws_exp.merge_cells("A8:B8")
    ws_exp.cell(row=8, column=1, value="إجمالي المصروفات والأعباء").font = total_font
    ws_exp.cell(row=8, column=1).alignment = align_center
    ws_exp.cell(row=8, column=1).fill = total_fill

    cell_tot_exp = ws_exp.cell(row=8, column=3, value='=SUM(C3:C7)')
    cell_tot_exp.font = total_font; cell_tot_exp.fill = total_fill; cell_tot_exp.number_format = num_fmt; cell_tot_exp.border = border_total

    cell_pct_exp = ws_exp.cell(row=8, column=4, value='=SUM(D3:D7)')
    cell_pct_exp.font = total_font; cell_pct_exp.fill = total_fill; cell_pct_exp.number_format = pct_fmt; cell_pct_exp.border = border_total; cell_pct_exp.alignment = align_center

    cell_pct_sales = ws_exp.cell(row=8, column=5, value='=C8/قائمة_الدخل!$D$7')
    cell_pct_sales.font = total_font; cell_pct_sales.fill = total_fill; cell_pct_sales.number_format = pct_fmt; cell_pct_sales.border = border_total; cell_pct_sales.alignment = align_center

    for c in [6, 7]:
        ws_exp.cell(row=8, column=c).border = border_total; ws_exp.cell(row=8, column=c).fill = total_fill

    # Auto-adjust column widths
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if val.startswith("="):
                    val_len = 12
                else:
                    val_len = len(val)
                if val_len > max_len:
                    max_len = val_len
            ws.column_dimensions[col_letter].width = max(max_len + 5, 14)

    ws_dash.column_dimensions['A'].width = 6
    ws_dash.column_dimensions['B'].width = 24
    ws_dash.column_dimensions['C'].width = 18
    ws_dash.column_dimensions['D'].width = 24
    ws_dash.column_dimensions['E'].width = 18
    ws_dash.column_dimensions['F'].width = 26
    ws_dash.column_dimensions['G'].width = 18
    ws_dash.column_dimensions['H'].width = 26
    ws_dash.column_dimensions['I'].width = 18

    if "Sheet" in wb.sheetnames:
        wb.remove(wb["Sheet"])

    output_path = r"i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster\النظام_المحاسبي_المتقدم_الشامل.xlsx"
    wb.save(output_path)
    print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    build_accounting_system()
