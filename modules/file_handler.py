import os


def scan_and_categorize(directory):
    """
    يفحص المجلد المحدد، يصنف الملفات، ويعيد قاموساً بالتصنيفات وقائمة بكل مسارات الملفات.
    """
    categories_map = {
        "📄 المستندات": ["pdf", "docx", "doc", "txt"],
        "📄 عرضو تقديمية": ["pptx", "ppt"],
        "📊 جداول البيانات": ["xlsx", "xls", "csv"],
        "🗜️ ملفات مضغوطة": ["zip", "rar", "7z"],
        "🎬 فيديو": ["mp4", "mkv", "avi", "mov", "wmv"],
        "🎵 صوت": ["mp3", "wav", "ogg", "flac"],
        "🖼️ صور": ["jpg", "jpeg", "png", "gif", "bmp"],
    }

    # تهيئة القواميس والقوائم
    categorized_files = {cat: [] for cat in categories_map}
    all_paths = []

    if not os.path.isdir(directory):
        return categorized_files, all_paths

    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            all_paths.append(full_path)  # تخزين المسار الكامل

            extension = file.split(".")[-1].lower()
            for category_name, exts in categories_map.items():
                if extension in exts:
                    # إضافة اسم الملف فقط للقائمة للعرض
                    categorized_files[category_name].append(file)
                    break

    return categorized_files, all_paths
