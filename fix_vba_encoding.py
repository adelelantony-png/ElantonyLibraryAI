# -*- coding: utf-8 -*-
"""
Script to fix the VBA encoding issue permanently:
1. Rewrites Accounting_VBA_Suite with clean code and native Windows MessageBoxW support
2. Saves it in cp1256 (Windows Arabic ANSI) encoding
3. Imports it into both XLSM files cleanly
"""

import os
import shutil
import win32com.client

vba_code_text = '''Attribute VB_Name = "Accounting_VBA_Suite"
'========================================================================================
' Advanced Financial Accounting System - Enterprise VBA Suite
' System Architecture: Normalized Ledger with English Sheet Naming & Arabic Content
' Company: Mahmoud Khalifa Trading & Import/Export Co. (S.A.E)
' Encoding: Windows-1256 (Arabic ANSI) - Compatible with Microsoft VBA Editor
'========================================================================================

Option Explicit

' Default system protection password
Public Const SYSTEM_PASSWORD As String = "123"

' Native Windows Unicode Message Box API to guarantee 100% crisp Arabic text on all machines
#If VBA7 Then
    Private Declare PtrSafe Function MessageBoxW Lib "user32" ( _
        ByVal hwnd As LongPtr, ByVal lpText As LongPtr, ByVal lpCaption As LongPtr, ByVal uType As Long) As Long
#Else
    Private Declare Function MessageBoxW Lib "user32" ( _
        ByVal hwnd As Long, ByVal lpText As Long, ByVal lpCaption As Long, ByVal uType As Long) As Long
#End If

' Custom Unicode Message Box Wrapper
Public Function AlertMsg(ByVal pMessage As String, Optional ByVal pButtons As VbMsgBoxStyle = vbInformation, Optional ByVal pTitle As String = "نظام الإدارة المالية") As Long
    AlertMsg = MessageBoxW(0, StrPtr(pMessage), StrPtr(pTitle), pButtons)
End Function

'----------------------------------------------------------------------------------------
' 1. Post New Journal Entry with Strict Balancing
'----------------------------------------------------------------------------------------
Public Sub PostNewJournalEntry(ByVal pDate As Date, _
                               ByVal pAccCode As String, _
                               ByVal pEntity As String, _
                               ByVal pDesc As String, _
                               ByVal pDebit As Double, _
                               ByVal pCredit As Double, _
                               ByVal pDocRef As String)
    Dim wsGL As Worksheet
    Dim lastRow As Long
    Dim nextEntryNo As Long
    
    Set wsGL = ThisWorkbook.Sheets("General_Ledger")
    
    On Error Resume Next
    wsGL.Unprotect SYSTEM_PASSWORD
    On Error GoTo 0
    
    lastRow = wsGL.Cells(wsGL.Rows.Count, "E").End(xlUp).Row
    
    If lastRow >= 3 Then
        nextEntryNo = wsGL.Cells(lastRow, 2).Value
    Else
        nextEntryNo = 1
    End If
    
    lastRow = lastRow + 1
    wsGL.Cells(lastRow, 1).Value = lastRow - 2                      ' مسلسل
    wsGL.Cells(lastRow, 2).Value = nextEntryNo                      ' رقم القيد
    wsGL.Cells(lastRow, 3).Value = Format(pDate, "yyyy-mm-dd")      ' التاريخ
    wsGL.Cells(lastRow, 4).Value = Month(pDate)                     ' الشهر
    wsGL.Cells(lastRow, 5).Value = pAccCode                         ' كود الحساب
    wsGL.Cells(lastRow, 6).Formula = "=VLOOKUP(E" & lastRow & ", COA!A:B, 2, FALSE)" ' اسم الحساب
    wsGL.Cells(lastRow, 7).Value = pEntity                          ' الطرف
    wsGL.Cells(lastRow, 8).Value = pDesc                            ' البيان
    wsGL.Cells(lastRow, 9).Value = pDebit                           ' مدين
    wsGL.Cells(lastRow, 10).Value = pCredit                         ' دائن
    wsGL.Cells(lastRow, 11).Value = pDocRef                         ' رقم المستند
    wsGL.Cells(lastRow, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRow & ")=SUMIFS($J:$J, $B:$B, B" & lastRow & "), ""متزن"", ""غير متزن"")"
    
    wsGL.Range("I" & lastRow & ":J" & lastRow).NumberFormat = "#,##0.00"
End Sub

'----------------------------------------------------------------------------------------
' 2. Navigate to Next Entry in General Ledger
'----------------------------------------------------------------------------------------
Public Sub GoToNewEntry()
    Dim wsGL As Worksheet
    Dim lastRow As Long
    
    Set wsGL = ThisWorkbook.Sheets("General_Ledger")
    wsGL.Activate
    lastRow = wsGL.Cells(wsGL.Rows.Count, "E").End(xlUp).Row + 1
    wsGL.Cells(lastRow, 2).Select
    
    AlertMsg "تم الانتقال إلى سطر إدخال القيد الجديد في دفتر اليومية العامة (رقم السطر: " & (lastRow - 2) & ")." & vbCrLf & _
             "أدخل بيانات القيد وسيقوم النظام بفحص الاتزان التلقائي فورياً.", vbInformation, "تسجيل قيد جديد"
End Sub

'----------------------------------------------------------------------------------------
' 3. Generate Dynamic Account Statement
'----------------------------------------------------------------------------------------
Public Sub GenerateAccountStatement()
    Dim wsGL As Worksheet, wsStmt As Worksheet
    Dim targetCode As String
    Dim lastRowGL As Long, outRow As Long, i As Long
    Dim runningBalance As Double
    Dim accNature As String
    
    Set wsGL = ThisWorkbook.Sheets("General_Ledger")
    Set wsStmt = ThisWorkbook.Sheets("Account_Statement")
    
    targetCode = Trim(wsStmt.Range("C3").Value)
    If targetCode = "" Then
        AlertMsg "برجاء كتابة كود الحساب في الخلية C3 أولاً للاستعلام", vbExclamation, "تنبيه مطلوب كود الحساب"
        Exit Sub
    End If
    
    On Error Resume Next
    wsStmt.Unprotect SYSTEM_PASSWORD
    On Error GoTo 0
    
    wsStmt.Range("A8:G1000").ClearContents
    
    accNature = Trim(wsStmt.Range("G3").Value)
    runningBalance = 0
    outRow = 8
    
    lastRowGL = wsGL.Cells(wsGL.Rows.Count, "E").End(xlUp).Row
    
    Application.ScreenUpdating = False
    
    For i = 3 To lastRowGL
        If Trim(CStr(wsGL.Cells(i, 5).Value)) = targetCode Then
            wsStmt.Cells(outRow, 1).Value = wsGL.Cells(i, 3).Value ' التاريخ
            wsStmt.Cells(outRow, 2).Value = wsGL.Cells(i, 2).Value ' رقم القيد
            wsStmt.Cells(outRow, 3).Value = wsGL.Cells(i, 7).Value ' الطرف
            wsStmt.Cells(outRow, 4).Value = wsGL.Cells(i, 8).Value ' البيان
            wsStmt.Cells(outRow, 5).Value = wsGL.Cells(i, 9).Value ' مدين
            wsStmt.Cells(outRow, 6).Value = wsGL.Cells(i, 10).Value ' دائن
            
            If accNature = "مدين" Then
                runningBalance = runningBalance + wsGL.Cells(i, 9).Value - wsGL.Cells(i, 10).Value
            Else
                runningBalance = runningBalance + wsGL.Cells(i, 10).Value - wsGL.Cells(i, 9).Value
            End If
            wsStmt.Cells(outRow, 7).Value = runningBalance
            
            wsStmt.Range("E" & outRow & ":G" & outRow).NumberFormat = "#,##0.00"
            outRow = outRow + 1
        End If
    Next i
    
    Application.ScreenUpdating = True
    
    If outRow = 8 Then
        AlertMsg "لا توجد حركات مسجلة لهذا الحساب (" & targetCode & ") في دفتر اليومية.", vbInformation, "نتيجة البحث"
    Else
        AlertMsg "تم استخراج كشف الحساب بنجاح لعدد " & (outRow - 8) & " حركة." & vbCrLf & _
                 "الرصيد الختامي الصافي: " & Format(runningBalance, "#,##0.00") & " ج.م", vbInformation, "تم بنجاح"
    End If
End Sub

'----------------------------------------------------------------------------------------
' 4. Auto-Generate Depreciation Adjusting Entry
'----------------------------------------------------------------------------------------
Public Sub AutoGenerateDepreciationEntry()
    Dim wsAst As Worksheet, wsGL As Worksheet
    Dim totalDepr As Double
    Dim lastRowGL As Long, newEntryNo As Long
    
    Set wsAst = ThisWorkbook.Sheets("Assets_Register")
    Set wsGL = ThisWorkbook.Sheets("General_Ledger")
    
    totalDepr = wsAst.Range("J6").Value
    
    If totalDepr <= 0 Then
        AlertMsg "إجمالي قسط الإهلاك يساوي صفر أو لم يتم تسجيل أصول بالسجل!", vbExclamation, "تنبيه"
        Exit Sub
    End If
    
    If AlertMsg("هل تريد ترحيل قيد تسوية إهلاك الأصول السنوي بمبلغ: " & Format(totalDepr, "#,##0.00") & " ج.م؟", vbQuestion + vbYesNo, "تأكيد الترحيل") = vbNo Then
        Exit Sub
    End If
    
    On Error Resume Next
    wsGL.Unprotect SYSTEM_PASSWORD
    On Error GoTo 0
    
    lastRowGL = wsGL.Cells(wsGL.Rows.Count, "E").End(xlUp).Row
    newEntryNo = wsGL.Cells(lastRowGL, 2).Value + 1
    
    ' طرف مدين: مصروف إهلاك
    lastRowGL = lastRowGL + 1
    wsGL.Cells(lastRowGL, 1).Value = lastRowGL - 2
    wsGL.Cells(lastRowGL, 2).Value = newEntryNo
    wsGL.Cells(lastRowGL, 3).Value = Format(DateSerial(Year(Date), 12, 31), "yyyy-mm-dd")
    wsGL.Cells(lastRowGL, 4).Value = 12
    wsGL.Cells(lastRowGL, 5).Value = "5240"
    wsGL.Cells(lastRowGL, 6).Formula = "=VLOOKUP(E" & lastRowGL & ", COA!A:B, 2, FALSE)"
    wsGL.Cells(lastRowGL, 7).Value = "تسويات جردية"
    wsGL.Cells(lastRowGL, 8).Value = "إثبات قسط إهلاك الأصول الثابتة السنوي الآلي"
    wsGL.Cells(lastRowGL, 9).Value = totalDepr
    wsGL.Cells(lastRowGL, 10).Value = 0
    wsGL.Cells(lastRowGL, 11).Value = "تسوية آلي"
    wsGL.Cells(lastRowGL, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRowGL & ")=SUMIFS($J:$J, $B:$B, B" & lastRowGL & "), ""متزن"", ""غير متزن"")"
    
    ' طرف دائن: مجمع إهلاك
    lastRowGL = lastRowGL + 1
    wsGL.Cells(lastRowGL, 1).Value = lastRowGL - 2
    wsGL.Cells(lastRowGL, 2).Value = newEntryNo
    wsGL.Cells(lastRowGL, 3).Value = Format(DateSerial(Year(Date), 12, 31), "yyyy-mm-dd")
    wsGL.Cells(lastRowGL, 4).Value = 12
    wsGL.Cells(lastRowGL, 5).Value = "1190"
    wsGL.Cells(lastRowGL, 6).Formula = "=VLOOKUP(E" & lastRowGL & ", COA!A:B, 2, FALSE)"
    wsGL.Cells(lastRowGL, 7).Value = "تسويات جردية"
    wsGL.Cells(lastRowGL, 8).Value = "إثبات مجمع إهلاك الأصول الثابتة السنوي الآلي"
    wsGL.Cells(lastRowGL, 9).Value = 0
    wsGL.Cells(lastRowGL, 10).Value = totalDepr
    wsGL.Cells(lastRowGL, 11).Value = "تسوية آلي"
    wsGL.Cells(lastRowGL, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRowGL & ")=SUMIFS($J:$J, $B:$B, B" & lastRowGL & "), ""متزن"", ""غير متزن"")"
    
    wsGL.Range("I" & (lastRowGL - 1) & ":J" & lastRowGL).NumberFormat = "#,##0.00"
    
    AlertMsg "تم ترحيل قيد تسوية الإهلاك بنجاح إلى اليومية العامة برقم: " & newEntryNo, vbInformation, "تم بنجاح"
End Sub

'----------------------------------------------------------------------------------------
' 5. Export Financial Statements to PDF
'----------------------------------------------------------------------------------------
Public Sub ExportFinancialStatementsToPDF()
    Dim wsList As Variant
    Dim folderPath As String
    Dim fileName As String
    
    folderPath = ThisWorkbook.Path & "\\"
    fileName = folderPath & "Financial_Statements_Report_" & Format(Now, "yyyy-mm-dd_hhmm") & ".pdf"
    
    wsList = Array("Income_Statement", "Balance_Sheet", "Cash_Flow", "Trial_Balance")
    
    On Error GoTo ErrHandler
    ThisWorkbook.Sheets(wsList).Select
    ActiveSheet.ExportAsFixedFormat Type:=xlTypePDF, fileName:=fileName, _
        Quality:=xlQualityStandard, IncludeDocProperties:=True, _
        IgnorePrintAreas:=False, OpenAfterPublish:=True
        
    ThisWorkbook.Sheets("Dashboard").Select
    AlertMsg "تم تصدير القوائم المالية بنجاح بصيغة PDF في المسار:" & vbCrLf & fileName, vbInformation, "تم التصدير"
    Exit Sub
    
ErrHandler:
    ThisWorkbook.Sheets("Dashboard").Select
    AlertMsg "حدث خطأ أثناء تصدير ملف الـ PDF: " & Err.Description, vbCritical, "تنبيه خطأ"
End Sub

'----------------------------------------------------------------------------------------
' 6. Create Instant Timestamped Backup
'----------------------------------------------------------------------------------------
Public Sub CreateInstantBackup()
    Dim backupFolder As String
    Dim backupName As String
    
    backupFolder = ThisWorkbook.Path & "\\Backups\\"
    If Dir(backupFolder, vbDirectory) = "" Then
        MkDir backupFolder
    End If
    
    backupName = backupFolder & "Backup_" & Format(Now, "yyyy-mm-dd_hh-nn-ss") & ".xlsm"
    
    On Error GoTo ErrHandler
    ThisWorkbook.SaveCopyAs backupName
    AlertMsg "تم إنشاء وحفظ نسخة احتياطية آمنة للملف بنجاح في:" & vbCrLf & backupName, vbInformation, "النسخ الاحتياطي"
    Exit Sub
    
ErrHandler:
    AlertMsg "تعذر حفظ النسخة الاحتياطية: " & Err.Description, vbCritical, "تنبيه خطأ"
End Sub

'----------------------------------------------------------------------------------------
' 7. Refresh All Reports
'----------------------------------------------------------------------------------------
Public Sub RefreshAllReports()
    Application.ScreenUpdating = False
    Application.CalculateFull
    Application.ScreenUpdating = True
    AlertMsg "تم تحديث كافة المعادلات، ميزان المراجعة، ومؤشرات الأداء المالي بنجاح.", vbInformation, "تم التحديث"
End Sub

'----------------------------------------------------------------------------------------
' 8. Protect System Formulas
'----------------------------------------------------------------------------------------
Public Sub ProtectSystemFormulas()
    Dim ws As Worksheet
    
    For Each ws In ThisWorkbook.Worksheets
        ws.Protect Password:=SYSTEM_PASSWORD, DrawingObjects:=False, Contents:=True, _
                   Scenarios:=True, UserInterfaceOnly:=True
    Next ws
    
    AlertMsg "تم تفعيل حماية المعادلات لكافة أوراق العمل بنجاح." & vbCrLf & _
             "كلمة المرور الافتراضية هي: " & SYSTEM_PASSWORD, vbInformation, "تأمين النظام"
End Sub

'----------------------------------------------------------------------------------------
' 9. Unprotect System
'----------------------------------------------------------------------------------------
Public Sub UnprotectSystem()
    Dim ws As Worksheet
    Dim pwd As String
    
    pwd = InputBox("أدخل كلمة المرور لإلغاء حماية النظام:", "إلغاء الحماية")
    If pwd <> SYSTEM_PASSWORD Then
        AlertMsg "كلمة المرور غير صحيحة!", vbCritical, "تم الرفض"
        Exit Sub
    End If
    
    For Each ws In ThisWorkbook.Worksheets
        On Error Resume Next
        ws.Unprotect Password:=pwd
        On Error GoTo 0
    Next ws
    
    AlertMsg "تم إلغاء حماية أوراق العمل بنجاح.", vbInformation, "تم الإلغاء"
End Sub

'----------------------------------------------------------------------------------------
' 10. Navigation Macro: Go to Dashboard
'----------------------------------------------------------------------------------------
Public Sub GoToDashboard()
    ThisWorkbook.Sheets("Dashboard").Activate
End Sub
'''

temp_dir = os.environ.get('TEMP', r'C:\Windows\Temp')
base_dir = os.path.abspath(r'i:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster')

bas_file = os.path.join(base_dir, "Accounting_VBA_Suite.bas")
temp_bas_1256 = os.path.join(temp_dir, "Accounting_VBA_Suite_1256.bas")

# Write to file in cp1256 encoding (Windows Arabic ANSI)
with open(temp_bas_1256, 'wb') as f:
    f.write(vba_code_text.encode('cp1256'))

with open(bas_file, 'wb') as f:
    f.write(vba_code_text.encode('cp1256'))

print("Accounting_VBA_Suite.bas successfully saved in CP1256 encoding.")

# Re-import into both XLSM files
xlsm_benchmark = os.path.join(base_dir, "النظام_المحاسبي_المتقدم_الشامل.xlsm")
xlsm_production = os.path.join(base_dir, "النظام_المحاسبي_التشغيلي_الفارغ.xlsm")

temp_bench = os.path.join(temp_dir, "bench_reimport.xlsm")
temp_prod = os.path.join(temp_dir, "prod_reimport.xlsm")

shutil.copyfile(xlsm_benchmark, temp_bench)
shutil.copyfile(xlsm_production, temp_prod)

xl = win32com.client.Dispatch("Excel.Application")
xl.Visible = False
xl.DisplayAlerts = False

for target_file, orig_file in [(temp_bench, xlsm_benchmark), (temp_prod, xlsm_production)]:
    wb = xl.Workbooks.Open(target_file)
    for comp in list(wb.VBProject.VBComponents):
        if comp.Name == "Accounting_VBA_Suite":
            wb.VBProject.VBComponents.Remove(comp)
    wb.VBProject.VBComponents.Import(temp_bas_1256)
    wb.Save()
    wb.Close()
    shutil.copyfile(target_file, orig_file)
    print(f"Re-imported clean CP1256 VBA module into: {os.path.basename(orig_file)}")

xl.Quit()
print("ALL DONE: Arabic character encoding permanently resolved!")
