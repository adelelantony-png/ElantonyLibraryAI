import os
import re
from modules import database_handler, ocr_handler


def find_files_to_rename(root_folder_id):
    """
    يبحث في قاعدة البيانات عن الملفات التي يحتمل أن تحتاج إلى إعادة تسمية
    داخل المشروع المحدد.
    """
    if not root_folder_id:
        return []
        
    patterns = ["IMG_%", "SCAN%", "Scan%", "Screenshot%", "Screen Shot%", "Image%"]
    
    files_from_patterns = database_handler.get_files_matching_patterns(patterns, root_folder_id)
    numeric_files = database_handler.get_files_with_numeric_names(root_folder_id)
    
    all_files = {file[0]: file for file in files_from_patterns + numeric_files}
    
    return list(all_files.values())


def suggest_new_name(file_path):
    """
    يقرأ محتوى الملف ويحاول اقتراح اسم جديد وذكي بناءً على الأنماط.
    """
    try:
        details = database_handler.get_file_details_for_ai(file_path)
        text = ""
        if details and details[1]:
             text = details[1]
        else:
             text = ocr_handler.extract_text(file_path)

        if not text:
            return ""

        text_sample = text[:2000].lower()

        date_str = ""
        match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}[-/]\d{1,2}[-/]\d{4})", text_sample)
        if match:
            date_group = match.group(1) if match.group(1) else match.group(2)
            parts = re.split(r'[-/]', date_group)
            try:
                if len(parts[0]) == 4:
                    date_str = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                else:
                    date_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except IndexError:
                date_str = ""
        else:
            match = re.search(
                r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})",
                text_sample,
                re.IGNORECASE,
            )
            if match:
                day, month_name, year = match.groups()
                month_map = {
                    "january": "01", "february": "02", "march": "03", "april": "04", 
                    "may": "05", "june": "06", "july": "07", "august": "08", 
                    "september": "09", "october": "10", "november": "11", "december": "12",
                }
                month = month_map[month_name.lower()]
                date_str = f"{year}-{month}-{day.zfill(2)}"

        title = ""
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 3]
        if lines:
            first_line = lines[0]
            title = re.sub(r'[^\w\s-]', '', first_line).strip()
            title = title[:50]

        keywords = {
            "فاتورة": "Invoice", "إيصال": "Receipt", "عقد": "Contract", "تقرير": "Report",
            "شهادة": "Certificate", "هوية": "ID", "عرض سعر": "Quotation", "سيرة ذاتية": "CV"
        }
        doc_type = ""
        for ar_key, en_val in keywords.items():
            if ar_key in text_sample or en_val.lower() in text_sample:
                doc_type = en_val
                break

        parts = []
        if date_str:
            parts.append(date_str)
        if doc_type:
            parts.append(doc_type)
        if title:
            if not doc_type or doc_type.lower() not in title.lower():
                parts.append(title)
        
        if not parts:
            return ""

        final_parts = []
        seen_parts = set()
        for part in parts:
            if part.lower() not in seen_parts:
                final_parts.append(part)
                seen_parts.add(part.lower())

        new_name = " - ".join(final_parts)
        new_name = re.sub(r'\s+', ' ', new_name).strip()
        new_name = new_name.strip(' -')

        return new_name

    except Exception as e:
        print(f"Error suggesting name for {file_path}: {e}")
        return ""