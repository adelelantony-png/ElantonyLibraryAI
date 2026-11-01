import os
from modules import database_handler


def check_condition(file_data, rule):
    condition_type = rule["condition_type"]
    condition_value = rule["condition_value"].lower()
    file_name = file_data["name"].lower()
    file_ext = file_data["ext"].lower()
    file_summary = file_data["summary"].lower() if file_data["summary"] else ""
    file_tags = file_data["tags"].lower() if file_data["tags"] else ""

    if condition_type == "المفهوم الرئيسي يحتوي على":
        return any(word in file_summary.split() for word in condition_value.split())
    elif condition_type == "اسم الملف يحتوي على":
        return condition_value in file_name
    elif condition_type == "نوع الملف هو":
        return condition_value.strip(".") == file_ext
    elif condition_type == "يحمل الوسم":
        return f"#{condition_value}#" in f"#{'#'.join(file_tags.split())}#"
    return False


def generate_organization_plan(root_folder_id, log_callback):
    log_callback("المحرك: جاري جلب القواعد والملفات من قاعدة البيانات...")
    rules = database_handler.get_all_rules()
    files = database_handler.get_all_files_for_engine(root_folder_id)
    suggestions = []
    if not rules:
        log_callback("المحرك: لا توجد قواعد تنظيم معرفة. توقفت العملية.")
        return []
    if not files:
        log_callback("المحرك: لا توجد ملفات مفهرسة لهذا المشروع. توقفت العملية.")
        return []

    parsed_rules = [
        {
            "id": r[0],
            "condition_type": r[1],
            "condition_value": r[2],
            "action_type": r[3],
            "action_value": r[4],
            "priority": r[5],
        }
        for r in rules
    ]
    log_callback(f"المحرك: بدء التحقق من {len(files)} ملف مقابل {len(rules)} قاعدة...")
    for file_info in files:
        file_data = {
            "id": file_info[0],
            "path": file_info[1],
            "name": file_info[2],
            "ext": file_info[3],
            "summary": file_info[4] or "",
            "tags": file_info[5] or "",
        }
        log_callback(f"--> التحقق من ملف: {file_data['name']}")
        for rule_data in parsed_rules:
            log_callback(
                f"    - ضد القاعدة رقم {rule_data['id']}: إذا كان '{rule_data['condition_type']}' يحتوي على '{rule_data['condition_value']}'"
            )
            if check_condition(file_data, rule_data):
                log_callback(
                    f"    [مطابقة!] الإجراء المقترح: '{rule_data['action_type']}' بالقيمة '{rule_data['action_value']}'"
                )
                if (
                    rule_data["action_type"] == "إضافة وسم"
                    and rule_data["action_value"] in file_data["tags"].split()
                ):
                    log_callback("    -> تم تخطي الإجراء لأن الوسم موجود بالفعل.")
                    continue
                suggestions.append(
                    {
                        "file_path": file_data["path"],
                        "file_id": file_data["id"],
                        "action_type": rule_data["action_type"],
                        "action_value": rule_data["action_value"],
                    }
                )
                break
    log_callback("المحرك: اكتملت عملية إنشاء الاقتراحات بنجاح.")
    return suggestions
