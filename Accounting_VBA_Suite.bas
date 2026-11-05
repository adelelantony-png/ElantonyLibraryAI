Attribute VB_Name = "Accounting_VBA_Suite"
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
Public Function AlertMsg(ByVal pMessage As String, Optional ByVal pButtons As VbMsgBoxStyle = vbInformation, Optional ByVal pTitle As String = "‰Ÿ«„ «·≈œ«—… «·„«·Ì…") As Long
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
    wsGL.Cells(lastRow, 1).Value = lastRow - 2                      ' „”·”·
    wsGL.Cells(lastRow, 2).Value = nextEntryNo                      ' —ﬁ„ «·ﬁÌœ
    wsGL.Cells(lastRow, 3).Value = Format(pDate, "yyyy-mm-dd")      ' «· «—ÌŒ
    wsGL.Cells(lastRow, 4).Value = Month(pDate)                     ' «·‘Â—
    wsGL.Cells(lastRow, 5).Value = pAccCode                         ' ﬂÊœ «·Õ”«»
    wsGL.Cells(lastRow, 6).Formula = "=VLOOKUP(E" & lastRow & ", COA!A:B, 2, FALSE)" ' «”„ «·Õ”«»
    wsGL.Cells(lastRow, 7).Value = pEntity                          ' «·ÿ—›
    wsGL.Cells(lastRow, 8).Value = pDesc                            ' «·»Ì«‰
    wsGL.Cells(lastRow, 9).Value = pDebit                           ' „œÌ‰
    wsGL.Cells(lastRow, 10).Value = pCredit                         ' œ«∆‰
    wsGL.Cells(lastRow, 11).Value = pDocRef                         ' —ﬁ„ «·„” ‰œ
    wsGL.Cells(lastRow, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRow & ")=SUMIFS($J:$J, $B:$B, B" & lastRow & "), ""„ “‰"", ""€Ì— „ “‰"")"
    
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
    
    AlertMsg " „ «·«‰ ﬁ«· ≈·Ï ”ÿ— ≈œŒ«· «·ﬁÌœ «·ÃœÌœ ›Ì œ› — «·ÌÊ„Ì… «·⁄«„… (—ﬁ„ «·”ÿ—: " & (lastRow - 2) & ")." & vbCrLf & _
             "√œŒ· »Ì«‰«  «·ﬁÌœ Ê”ÌﬁÊ„ «·‰Ÿ«„ »›Õ’ «·« “«‰ «· ·ﬁ«∆Ì ›Ê—Ì«.", vbInformation, " ”ÃÌ· ﬁÌœ ÃœÌœ"
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
        AlertMsg "»—Ã«¡ ﬂ «»… ﬂÊœ «·Õ”«» ›Ì «·Œ·Ì… C3 √Ê·« ··«” ⁄·«„", vbExclamation, " ‰»ÌÂ „ÿ·Ê» ﬂÊœ «·Õ”«»"
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
            wsStmt.Cells(outRow, 1).Value = wsGL.Cells(i, 3).Value ' «· «—ÌŒ
            wsStmt.Cells(outRow, 2).Value = wsGL.Cells(i, 2).Value ' —ﬁ„ «·ﬁÌœ
            wsStmt.Cells(outRow, 3).Value = wsGL.Cells(i, 7).Value ' «·ÿ—›
            wsStmt.Cells(outRow, 4).Value = wsGL.Cells(i, 8).Value ' «·»Ì«‰
            wsStmt.Cells(outRow, 5).Value = wsGL.Cells(i, 9).Value ' „œÌ‰
            wsStmt.Cells(outRow, 6).Value = wsGL.Cells(i, 10).Value ' œ«∆‰
            
            If accNature = "„œÌ‰" Then
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
        AlertMsg "·«  ÊÃœ Õ—ﬂ«  „”Ã·… ·Â–« «·Õ”«» (" & targetCode & ") ›Ì œ› — «·ÌÊ„Ì….", vbInformation, "‰ ÌÃ… «·»ÕÀ"
    Else
        AlertMsg " „ «” Œ—«Ã ﬂ‘› «·Õ”«» »‰Ã«Õ ·⁄œœ " & (outRow - 8) & " Õ—ﬂ…." & vbCrLf & _
                 "«·—’Ìœ «·Œ «„Ì «·’«›Ì: " & Format(runningBalance, "#,##0.00") & " Ã.„", vbInformation, " „ »‰Ã«Õ"
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
        AlertMsg "≈Ã„«·Ì ﬁ”ÿ «·≈Â·«ﬂ Ì”«ÊÌ ’›— √Ê ·„ Ì „  ”ÃÌ· √’Ê· »«·”Ã·!", vbExclamation, " ‰»ÌÂ"
        Exit Sub
    End If
    
    If AlertMsg("Â·  —Ìœ  —ÕÌ· ﬁÌœ  ”ÊÌ… ≈Â·«ﬂ «·√’Ê· «·”‰ÊÌ »„»·€: " & Format(totalDepr, "#,##0.00") & " Ã.„ø", vbQuestion + vbYesNo, " √ﬂÌœ «· —ÕÌ·") = vbNo Then
        Exit Sub
    End If
    
    On Error Resume Next
    wsGL.Unprotect SYSTEM_PASSWORD
    On Error GoTo 0
    
    lastRowGL = wsGL.Cells(wsGL.Rows.Count, "E").End(xlUp).Row
    newEntryNo = wsGL.Cells(lastRowGL, 2).Value + 1
    
    ' ÿ—› „œÌ‰: „’—Ê› ≈Â·«ﬂ
    lastRowGL = lastRowGL + 1
    wsGL.Cells(lastRowGL, 1).Value = lastRowGL - 2
    wsGL.Cells(lastRowGL, 2).Value = newEntryNo
    wsGL.Cells(lastRowGL, 3).Value = Format(DateSerial(Year(Date), 12, 31), "yyyy-mm-dd")
    wsGL.Cells(lastRowGL, 4).Value = 12
    wsGL.Cells(lastRowGL, 5).Value = "5240"
    wsGL.Cells(lastRowGL, 6).Formula = "=VLOOKUP(E" & lastRowGL & ", COA!A:B, 2, FALSE)"
    wsGL.Cells(lastRowGL, 7).Value = " ”ÊÌ«  Ã—œÌ…"
    wsGL.Cells(lastRowGL, 8).Value = "≈À»«  ﬁ”ÿ ≈Â·«ﬂ «·√’Ê· «·À«» … «·”‰ÊÌ «·¬·Ì"
    wsGL.Cells(lastRowGL, 9).Value = totalDepr
    wsGL.Cells(lastRowGL, 10).Value = 0
    wsGL.Cells(lastRowGL, 11).Value = " ”ÊÌ… ¬·Ì"
    wsGL.Cells(lastRowGL, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRowGL & ")=SUMIFS($J:$J, $B:$B, B" & lastRowGL & "), ""„ “‰"", ""€Ì— „ “‰"")"
    
    ' ÿ—› œ«∆‰: „Ã„⁄ ≈Â·«ﬂ
    lastRowGL = lastRowGL + 1
    wsGL.Cells(lastRowGL, 1).Value = lastRowGL - 2
    wsGL.Cells(lastRowGL, 2).Value = newEntryNo
    wsGL.Cells(lastRowGL, 3).Value = Format(DateSerial(Year(Date), 12, 31), "yyyy-mm-dd")
    wsGL.Cells(lastRowGL, 4).Value = 12
    wsGL.Cells(lastRowGL, 5).Value = "1190"
    wsGL.Cells(lastRowGL, 6).Formula = "=VLOOKUP(E" & lastRowGL & ", COA!A:B, 2, FALSE)"
    wsGL.Cells(lastRowGL, 7).Value = " ”ÊÌ«  Ã—œÌ…"
    wsGL.Cells(lastRowGL, 8).Value = "≈À»«  „Ã„⁄ ≈Â·«ﬂ «·√’Ê· «·À«» … «·”‰ÊÌ «·¬·Ì"
    wsGL.Cells(lastRowGL, 9).Value = 0
    wsGL.Cells(lastRowGL, 10).Value = totalDepr
    wsGL.Cells(lastRowGL, 11).Value = " ”ÊÌ… ¬·Ì"
    wsGL.Cells(lastRowGL, 12).Formula = "=IF(SUMIFS($I:$I, $B:$B, B" & lastRowGL & ")=SUMIFS($J:$J, $B:$B, B" & lastRowGL & "), ""„ “‰"", ""€Ì— „ “‰"")"
    
    wsGL.Range("I" & (lastRowGL - 1) & ":J" & lastRowGL).NumberFormat = "#,##0.00"
    
    AlertMsg " „  —ÕÌ· ﬁÌœ  ”ÊÌ… «·≈Â·«ﬂ »‰Ã«Õ ≈·Ï «·ÌÊ„Ì… «·⁄«„… »—ﬁ„: " & newEntryNo, vbInformation, " „ »‰Ã«Õ"
End Sub

'----------------------------------------------------------------------------------------
' 5. Export Financial Statements to PDF
'----------------------------------------------------------------------------------------
Public Sub ExportFinancialStatementsToPDF()
    Dim wsList As Variant
    Dim folderPath As String
    Dim fileName As String
    
    folderPath = ThisWorkbook.Path & "\"
    fileName = folderPath & "Financial_Statements_Report_" & Format(Now, "yyyy-mm-dd_hhmm") & ".pdf"
    
    wsList = Array("Income_Statement", "Balance_Sheet", "Cash_Flow", "Trial_Balance")
    
    On Error GoTo ErrHandler
    ThisWorkbook.Sheets(wsList).Select
    ActiveSheet.ExportAsFixedFormat Type:=xlTypePDF, fileName:=fileName, _
        Quality:=xlQualityStandard, IncludeDocProperties:=True, _
        IgnorePrintAreas:=False, OpenAfterPublish:=True
        
    ThisWorkbook.Sheets("Dashboard").Select
    AlertMsg " „  ’œÌ— «·ﬁÊ«∆„ «·„«·Ì… »‰Ã«Õ »’Ì€… PDF ›Ì «·„”«—:" & vbCrLf & fileName, vbInformation, " „ «· ’œÌ—"
    Exit Sub
    
ErrHandler:
    ThisWorkbook.Sheets("Dashboard").Select
    AlertMsg "ÕœÀ Œÿ√ √À‰«¡  ’œÌ— „·› «·‹ PDF: " & Err.Description, vbCritical, " ‰»ÌÂ Œÿ√"
End Sub

'----------------------------------------------------------------------------------------
' 6. Create Instant Timestamped Backup
'----------------------------------------------------------------------------------------
Public Sub CreateInstantBackup()
    Dim backupFolder As String
    Dim backupName As String
    
    backupFolder = ThisWorkbook.Path & "\Backups\"
    If Dir(backupFolder, vbDirectory) = "" Then
        MkDir backupFolder
    End If
    
    backupName = backupFolder & "Backup_" & Format(Now, "yyyy-mm-dd_hh-nn-ss") & ".xlsm"
    
    On Error GoTo ErrHandler
    ThisWorkbook.SaveCopyAs backupName
    AlertMsg " „ ≈‰‘«¡ ÊÕ›Ÿ ‰”Œ… «Õ Ì«ÿÌ… ¬„‰… ··„·› »‰Ã«Õ ›Ì:" & vbCrLf & backupName, vbInformation, "«·‰”Œ «·«Õ Ì«ÿÌ"
    Exit Sub
    
ErrHandler:
    AlertMsg " ⁄–— Õ›Ÿ «·‰”Œ… «·«Õ Ì«ÿÌ…: " & Err.Description, vbCritical, " ‰»ÌÂ Œÿ√"
End Sub

'----------------------------------------------------------------------------------------
' 7. Refresh All Reports
'----------------------------------------------------------------------------------------
Public Sub RefreshAllReports()
    Application.ScreenUpdating = False
    Application.CalculateFull
    Application.ScreenUpdating = True
    AlertMsg " „  ÕœÌÀ ﬂ«›… «·„⁄«œ·« ° „Ì“«‰ «·„—«Ã⁄…° Ê„ƒ‘—«  «·√œ«¡ «·„«·Ì »‰Ã«Õ.", vbInformation, " „ «· ÕœÌÀ"
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
    
    AlertMsg " „  ›⁄Ì· Õ„«Ì… «·„⁄«œ·«  ·ﬂ«›… √Ê—«ﬁ «·⁄„· »‰Ã«Õ." & vbCrLf & _
             "ﬂ·„… «·„—Ê— «·«› —«÷Ì… ÂÌ: " & SYSTEM_PASSWORD, vbInformation, " √„Ì‰ «·‰Ÿ«„"
End Sub

'----------------------------------------------------------------------------------------
' 9. Unprotect System
'----------------------------------------------------------------------------------------
Public Sub UnprotectSystem()
    Dim ws As Worksheet
    Dim pwd As String
    
    pwd = InputBox("√œŒ· ﬂ·„… «·„—Ê— ·≈·€«¡ Õ„«Ì… «·‰Ÿ«„:", "≈·€«¡ «·Õ„«Ì…")
    If pwd <> SYSTEM_PASSWORD Then
        AlertMsg "ﬂ·„… «·„—Ê— €Ì— ’ÕÌÕ…!", vbCritical, " „ «·—›÷"
        Exit Sub
    End If
    
    For Each ws In ThisWorkbook.Worksheets
        On Error Resume Next
        ws.Unprotect Password:=pwd
        On Error GoTo 0
    Next ws
    
    AlertMsg " „ ≈·€«¡ Õ„«Ì… √Ê—«ﬁ «·⁄„· »‰Ã«Õ.", vbInformation, " „ «·≈·€«¡"
End Sub

'----------------------------------------------------------------------------------------
' 10. Navigation Macro: Go to Dashboard
'----------------------------------------------------------------------------------------
Public Sub GoToDashboard()
    ThisWorkbook.Sheets("Dashboard").Activate
End Sub
