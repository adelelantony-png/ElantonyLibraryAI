import os
import sys
import shutil
import datetime
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def get_target_folder(filename):
    """Maps a book/document filename to its proper theological/church category."""
    fname = filename.lower()
    
    # 1. Church figures / Authors
    if any(k in fname for k in ['متى المسكين', 'متي المسكين', 'الاب متى', 'الأب متى']):
        return "ابونا متي المسكين"
    if any(k in fname for k in ['بيشوي كامل', 'بيشوى كامل']):
        return "ابونا بيشوي كامل"
    if any(k in fname for k in ['تادرس يعقوب', 'tadros y. malaty', 'tadros yacoub']):
        return "القمص تادرس يعقوب"
    if any(k in fname for k in ['شنودة الثالث', 'البابا شنوده', 'البابا شنودة', 'كرازة', 'keraza']):
        return "البابا شنودة الثالث"
    if any(k in fname for k in ['كيرلس السادس', 'البابا كيرلس']):
        return "شخصيات"
    if any(k in fname for k in ['اغريغوريوس', 'غريغوريوس']):
        return "الانبا اغريغوريوس"
    if any(k in fname for k in ['موسي', 'موسى', 'اسقفية الشباب', 'أسقفية الشباب']):
        return "الانبا موسي"
    if any(k in fname for k in ['مارك شنودة', 'مارك شنوده']):
        return "د مارك شنودة"
    if any(k in fname for k in ['مجدي اسحق', 'مجدى اسحق']):
        return "الطب النفسي"
    if any(k in fname for k in ['حلمي القمص', 'مدارس النقد', 'نقد كتابي']):
        return "النقد الكتابي-حلمي القمص"
    if any(k in fname for k in ['عبد المسيح بسيط', 'بارت ايرمان', 'بارت إيرمان', 'ديدات', 'عصمة الكتاب']):
        return "عقيدة"
    if any(k in fname for k in ['إيريس حبيب', 'يوسابيوس', 'تاريخ البطاركة', 'سير البيعة', 'المجامع المسكونية']):
        return "تاريخ الكنيسة"
    if any(k in fname for k in ['ابن كبر', 'مصباح الظلمة', 'ابن العسال', 'المجموع الصفوي', 'ابن سباع', 'الجوهرة النفيسة', 'الدسقولية']):
        return "أبائيات"
    if any(k in fname for k in ['بيمن اسقف ملوي', 'الانبا بيمن']):
        return "الانبا بيمن اسقف ملوي"
    if any(k in fname for k in ['بيشوي مطران دمياط', 'الأنبا بيشوي']):
        return "الانبا بيشوي"
    if any(k in fname for k in ['يؤانس']):
        return "الانبا يؤانس"
    if any(k in fname for k in ['اشعياء ميخائيل', 'إشعياء ميخائيل']):
        return "القمص اشعياء ميخائيل"
    if any(k in fname for k in ['مرقس عزيز']):
        return "القمص مرقس عزيز"
    if any(k in fname for k in ['بيشوي', 'بيشوى']):
        return "الانبا بيشوي"
    if any(k in fname for k in ['متاؤس', 'متاوس']):
        return "الانبا متاؤس"
    if any(k in fname for k in ['مكاريوس']):
        return "الانبا مكاريوس - اسقف المنيا"
        
# 2. Key Topics
    if any(k in fname for k in ['منهج', 'مناهج', 'التربية الكنسية', 'المجمع المقدس', 'الإبتدائي', 'الابتدائي', 'الإعدادي', 'الاعدادي', 'kg2', 'حضانة']):
        return "مناهج المجمع المقدس - مناهج البابا الافتتاحية"
    if any(k in fname for k in ['وسائل إيضاح', 'وسائل الايضاح', 'وسيلة إيضاح']):
        return "وسائل إيضاح"
    if any(k in fname for k in ['كيف نخدم', 'اعداد خدام', 'إعداد خدام', 'الخدمة والخدام', 'فلسفة التعليم', 'الدرس التفاعلي', 'اتبعني']):
        return "الخدمة والخدام"
    if any(k in fname for k in ['تفسير', 'انجيل', 'إنجيل', 'رسالة', 'سفر', 'مزامير', 'مزمور']):
        return "تفسير الكتاب المقدس"
    if any(k in fname for k in ['كتاب مقدس', 'دراسة الكتاب', 'تاريخ العهد', 'نقد كتابي', 'العهد القديم', 'العهد الجديد']):
        return "دراسة كتاب مقدس"
    if any(k in fname for k in ['قداس', 'شماس', 'أجبية', 'اجبية', 'خولاجي', 'طقس', 'liturgy', 'deacon', 'كفن']):
        return "طقس الكنيسة"
    if any(k in fname for k in ['لحن', 'ألحان', 'الحان', 'تسبحة', 'ابصلمودية']):
        return "كتب الحان"
    if any(k in fname for k in ['آباء', 'اباء', 'باترولوجي', 'patrology', 'فيلوكاليا', 'أقوال', 'اقوال', 'ديداكي', 'إغناطيوس', 'بوليكاربوس', 'اثناسيوس', 'أثناسيوس', 'كيرلس', 'ترتيليانوس', 'اكليمندس', 'إكليمندس', 'ساويرس']):
        return "أبائيات"
    if any(k in fname for k in ['عقيدة', 'لاهوت', 'تثليث', 'طبيعة المسيح', 'فداء', 'كفارة', 'بدع', 'وجود الله', 'أريوس', 'نسطور', 'إلحاد', 'الحاد']):
        return "عقيدة"
    if any(k in fname for k in ['تاريخ', 'مجمع', 'سنكسار', 'اضطهاد', 'شهداء', 'نيروز']):
        return "تاريخ الكنيسة"
    if any(k in fname for k in ['أسبوع الآلام', 'البصخة', 'اسبوع الالام']):
        return "أسبوع الألام"
    if any(k in fname for k in ['صوم', 'صيام']):
        return "صوم الرسل"
    if any(k in fname for k in ['عذراء', 'مريم', 'ثيؤطوكية']):
        return "العذراء مريم"
    if any(k in fname for k in ['أسرة', 'اسرة', 'زواج', 'تربية', 'مذبح عائلي', 'أمومة', 'خطوبة', 'حتى لا نفقد أولادنا']):
        return "الأسرة والمشورة"
    if any(k in fname for k in ['تنمية', 'نجاح', 'تواصل']):
        return "تنمية بشرية"
    if any(k in fname for k in ['قصص', 'قصة']):
        return "قصص روحية"
        
    return "كتب روحية"

def settle_loose_files(library_root, log_callback=None):
    """
    Scans the root folder of the library, moves any loose books into their proper category folder,
    and moves temporary/cache files into _System_Temp_Cache.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except Exception:
            pass
        
    _log(f"بدء تسكين وترتيب الملفات في: {library_root}")
    temp_cache_dir = os.path.join(library_root, "_System_Temp_Cache")
    os.makedirs(temp_cache_dir, exist_ok=True)
    
    existing_dirs = {d.lower(): d for d in os.listdir(library_root) if os.path.isdir(os.path.join(library_root, d))}
    all_root_entries = [f for f in os.listdir(library_root) if os.path.isfile(os.path.join(library_root, f))]
    
    excluded_files = ['فهرس_المكتبة_الذكية.xlsx', 'تحديث_الفهرس_تلقائياً.bat', '🔍_شاشة_البحث_الذكية.bat', 'تشغيل_برنامج_المكتبة.bat']
    files_to_process = [
        f for f in all_root_entries 
        if f not in excluded_files and not f.lower().endswith(('.bat', '.cmd', '.exe', '.lnk'))
    ]
    
    if not files_to_process:
        _log("المجلد الرئيسي نظيف تماماً ولا توجد ملفات متناثرة تحتاج إلى تسكين.")
        return 0, 0
        
    moved_books = 0
    moved_temp = 0
    
    for f in files_to_process:
        source_path = os.path.join(library_root, f)
        ext = os.path.splitext(f)[1].lower()
        
        # Temp / cache files
        if (f == 'cached' or f.startswith('~$') or 
            ext in ['.xlsm', '.py', '.json'] or 
            'worksheet' in f.lower() or 'book1' in f.lower()):
            
            dest_path = os.path.join(temp_cache_dir, f)
            try:
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                shutil.move(source_path, dest_path)
                moved_temp += 1
            except Exception as e:
                _log(f"تعذر نقل الملف المؤقت {f}: {e}")
            continue
            
        # Books and media
        target_category = get_target_folder(f)
        actual_folder_name = existing_dirs.get(target_category.lower(), target_category)
        target_dir = os.path.join(library_root, actual_folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        dest_path = os.path.join(target_dir, f)
        if os.path.exists(dest_path):
            base, ext_part = os.path.splitext(f)
            counter = 1
            while os.path.exists(os.path.join(target_dir, f"{base}_settled_{counter}{ext_part}")):
                counter += 1
            dest_path = os.path.join(target_dir, f"{base}_settled_{counter}{ext_part}")
            
        try:
            shutil.move(source_path, dest_path)
            moved_books += 1
            _log(f"تم تسكين: '{f}' -> مجلد [{actual_folder_name}]")
        except Exception as e:
            _log(f"خطأ أثناء تسكين {f}: {e}")
            
    _log(f"اكتمل التسكين: تم نقل {moved_books} كتاباً للمجلدات، و {moved_temp} ملفاً مؤقتاً للكاش.")
    return moved_books, moved_temp

def update_library_excel_catalog(library_root, log_callback=None):
    """
    Generates / refreshes the complete multi-tab Excel catalog with native hyperlinks.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
        try:
            print(msg)
        except Exception:
            pass
        
    output_excel = os.path.join(library_root, "فهرس_المكتبة_الذكية.xlsx")
    _log("جاري فحص المكتبة وتحديث ملف الإكسيل التفاعلي...")
    
    all_files = []
    pdf_files = []
    word_files = []
    ppt_files = []
    audio_files = []
    video_files = []
    media_files = []
    
    total_size = 0
    category_counts = defaultdict(int)
    category_sizes = defaultdict(int)
    
    for root, dirs, files in os.walk(library_root):
        rel_path = os.path.relpath(root, library_root)
        if any(skip in rel_path for skip in ['_Duplicates_Isolated', '_System_Temp_Cache', '_scripts', 'ArchiveMaster', 'venv', '.git']):
            continue
            
        for f in files:
            if f.startswith('~$') or f == 'فهرس_المكتبة_الذكية.xlsx':
                continue
                
            full_path = os.path.join(root, f)
            try:
                stat = os.stat(full_path)
                sz = stat.st_size
                mtime = stat.st_mtime
                mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                ext = os.path.splitext(f)[1].lower()
                
                parts = rel_path.split(os.sep) if rel_path != '.' else []
                main_cat = parts[0] if parts else "المجلد الرئيسي"
                sub_cat = os.path.join(*parts[1:]) if len(parts) > 1 else "-"
                
                item = {
                    "name": f,
                    "path": full_path,
                    "main_cat": main_cat,
                    "sub_cat": sub_cat,
                    "ext": ext.replace('.', '').upper() if ext else "OTHER",
                    "size_mb": round(sz / (1024**2), 2),
                    "size_bytes": sz,
                    "date": mod_date
                }
                
                all_files.append(item)
                total_size += sz
                category_counts[main_cat] += 1
                category_sizes[main_cat] += sz
                
                if ext in ['.pdf']:
                    pdf_files.append(item)
                elif ext in ['.docx', '.doc', '.rtf', '.txt']:
                    word_files.append(item)
                elif ext in ['.pptx', '.ppt', '.ppsx', '.pps']:
                    ppt_files.append(item)
                elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                    audio_files.append(item)
                elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']:
                    video_files.append(item)
                else:
                    media_files.append(item)
            except OSError:
                continue
                
    for flist in [all_files, pdf_files, word_files, ppt_files, audio_files, video_files, media_files]:
        flist.sort(key=lambda x: (x["main_cat"], x["name"].lower()))
        
    wb = openpyxl.Workbook()
    font_family = "Segoe UI"
    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    data_font = Font(name=font_family, size=10)
    link_font = Font(name=font_family, size=10, color="0563C1", underline="single", bold=True)
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'), right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'), bottom=Side(style='thin', color='E2E8F0')
    )
    
    # Dashboard Sheet
    ws_dash = wb.active
    ws_dash.title = "📊 لوحة المؤشرات والأقسام"
    ws_dash.views.sheetView[0].rightToLeft = True
    ws_dash.sheet_properties.tabColor = "1B365D"
    
    ws_dash.merge_cells("A1:D1")
    tcell = ws_dash["A1"]
    tcell.value = "✠ مكتبة الصليب القبطية - الفهرس ولوحة الإحصائيات ✠"
    tcell.fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    tcell.font = Font(name=font_family, size=14, bold=True, color="FFFFFF")
    tcell.alignment = Alignment(horizontal="center", vertical="center")
    ws_dash.row_dimensions[1].height = 36
    
    kpis = [
        ("إجمالي الكتب والملفات النشطة:", len(all_files)),
        ("الحجم الإجمالي الصافي للمكتبة:", f"{total_size / (1024**3):.2f} GB"),
        ("إجمالي الأقسام والتصنيفات الكنسية:", len(category_counts)),
        ("كتب ومستندات PDF:", len(pdf_files)),
        ("مستندات Word:", len(word_files)),
        ("عروض تقديمية PowerPoint:", len(ppt_files)),
        ("صوتيات وألحان كنسية:", len(audio_files)),
        ("مرئيات وفيديو:", len(video_files))
    ]
    for idx, (lbl, val) in enumerate(kpis):
        r = 3 + idx
        ws_dash.cell(row=r, column=1, value=lbl).font = Font(name=font_family, size=10, bold=True, color="1B365D")
        ws_dash.cell(row=r, column=2, value=val).font = Font(name=font_family, size=10, bold=True)
        ws_dash.cell(row=r, column=1).alignment = Alignment(horizontal="right", vertical="center")
        ws_dash.cell(row=r, column=2).alignment = Alignment(horizontal="center", vertical="center")
        ws_dash.cell(row=r, column=1).border = border_thin
        ws_dash.cell(row=r, column=2).border = border_thin
        ws_dash.cell(row=r, column=1).fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        ws_dash.cell(row=r, column=2).fill = white_fill
        ws_dash.row_dimensions[r].height = 22
        
    start_cat_row = 12
    ws_dash.cell(row=start_cat_row, column=1, value="م").fill = PatternFill(start_color="2E5B88", end_color="2E5B88", fill_type="solid")
    ws_dash.cell(row=start_cat_row, column=2, value="القسم / التصنيف الكنسي").fill = PatternFill(start_color="2E5B88", end_color="2E5B88", fill_type="solid")
    ws_dash.cell(row=start_cat_row, column=3, value="عدد الكتب والملفات").fill = PatternFill(start_color="2E5B88", end_color="2E5B88", fill_type="solid")
    ws_dash.cell(row=start_cat_row, column=4, value="الحجم (ميجابايت)").fill = PatternFill(start_color="2E5B88", end_color="2E5B88", fill_type="solid")
    for c in range(1, 5):
        cell = ws_dash.cell(row=start_cat_row, column=c)
        cell.font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
        
    for idx, (cat_name, count) in enumerate(sorted(category_counts.items(), key=lambda x: x[1], reverse=True), 1):
        r = start_cat_row + idx
        ws_dash.cell(row=r, column=1, value=idx).alignment = Alignment(horizontal="center", vertical="center")
        ws_dash.cell(row=r, column=2, value=cat_name).alignment = Alignment(horizontal="right", vertical="center")
        ws_dash.cell(row=r, column=3, value=count).alignment = Alignment(horizontal="center", vertical="center")
        ws_dash.cell(row=r, column=4, value=round(category_sizes[cat_name] / (1024**2), 1)).alignment = Alignment(horizontal="right", vertical="center")
        c_fill = zebra_fill if idx % 2 == 0 else white_fill
        for c in range(1, 5):
            cell = ws_dash.cell(row=r, column=c)
            cell.font = data_font
            cell.border = border_thin
            cell.fill = c_fill
            
    ws_dash.column_dimensions["A"].width = 8
    ws_dash.column_dimensions["B"].width = 38
    ws_dash.column_dimensions["C"].width = 20
    ws_dash.column_dimensions["D"].width = 18
    
    # Data Sheets Helper
    def add_sheet(title, tab_col, head_col, flist):
        ws = wb.create_sheet(title=title)
        ws.views.sheetView[0].rightToLeft = True
        ws.sheet_properties.tabColor = tab_col
        headers = ["م", "اسم الكتاب / الملف", "📖 فتح مباشر", "التصنيف الكنسي", "المجلد الفرعي / القسم", "النوع", "الحجم (MB)", "تاريخ التعديل", "المسار الكامل"]
        ws.append(headers)
        h_fill = PatternFill(start_color=head_col, end_color=head_col, fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=1, column=col_idx)
            c.fill = h_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_thin
        ws.row_dimensions[1].height = 28
        
        for idx, item in enumerate(flist, 1):
            r = idx + 1
            curr_fill = zebra_fill if idx % 2 == 0 else white_fill
            ws.append([idx, item["name"], "📖 فتح الملف", item["main_cat"], item["sub_cat"], item["ext"], item["size_mb"], item["date"], item["path"]])
            ws.cell(row=r, column=1).alignment = Alignment(horizontal="center", vertical="center")
            
            c2 = ws.cell(row=r, column=2)
            c2.hyperlink = item["path"]
            c2.font = link_font
            c2.alignment = Alignment(horizontal="right", vertical="center")
            
            c3 = ws.cell(row=r, column=3)
            c3.hyperlink = item["path"]
            c3.font = link_font
            c3.alignment = Alignment(horizontal="center", vertical="center")
            
            ws.cell(row=r, column=4).alignment = Alignment(horizontal="right", vertical="center")
            ws.cell(row=r, column=5).alignment = Alignment(horizontal="right", vertical="center")
            ws.cell(row=r, column=6).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=r, column=7).alignment = Alignment(horizontal="right", vertical="center")
            ws.cell(row=r, column=8).alignment = Alignment(horizontal="center", vertical="center")
            ws.cell(row=r, column=9).alignment = Alignment(horizontal="left", vertical="center")
            
            for col_idx in range(1, 10):
                c = ws.cell(row=r, column=col_idx)
                c.border = border_thin
                c.fill = curr_fill
                if col_idx not in (2, 3):
                    c.font = data_font
            ws.row_dimensions[r].height = 22
            
        col_widths = {1: 8, 2: 45, 3: 15, 4: 28, 5: 30, 6: 10, 7: 14, 8: 18, 9: 35}
        for col_idx, width in col_widths.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:I{len(flist) + 1}"

    add_sheet("📚 الفهرس الشامل (الكل)", "1B365D", "1B365D", all_files)
    add_sheet("📄 كتب ومستندات PDF", "DC2626", "991B1B", pdf_files)
    add_sheet("📝 ملفات وورد Word", "2563EB", "1E40AF", word_files)
    add_sheet("🖥️ عروض تقديمية PowerPoint", "EA580C", "C2410C", ppt_files)
    add_sheet("🎵 صوتيات وألحان", "7C3AED", "6D28D9", audio_files)
    add_sheet("🎬 مرئيات وفيديو", "059669", "047857", video_files)
    add_sheet("🖼️ صور وخطوط كنسية", "0D9488", "0F766E", media_files)
    
    wb.save(output_excel)
    _log(f"تم حفظ تحديثات الإكسيل بنجاح في: {output_excel}")
    return len(all_files)
