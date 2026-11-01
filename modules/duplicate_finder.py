import os
import hashlib
from collections import defaultdict


def hash_file(path, block_size=65536):
    """
    دالة مساعدة لإنشاء "بصمة" (hash) فريدة لمحتوى الملف.
    """
    hasher = hashlib.md5()
    try:
        with open(path, "rb") as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
    except (IOError, OSError):
        # في حالة عدم القدرة على قراءة الملف، يتم تجاهله
        return None


def find_duplicates(file_paths):
    """
    تبحث عن الملفات المكررة ضمن قائمة المسارات المعطاة.
    الخطوة 1: تجمع الملفات حسب الحجم.
    الخطوة 2: للملفات المتساوية في الحجم فقط، تقوم بمقارنة بصمة المحتوى.
    """
    if not file_paths:
        return []

    # الخطوة 1: تجميع الملفات حسب الحجم
    files_by_size = defaultdict(list)
    for path in file_paths:
        try:
            # التأكد من أن المسار موجود بالفعل وأنه ملف
            if os.path.isfile(path):
                size = os.path.getsize(path)
                # تجاهل الملفات الفارغة
                if size > 0:
                    files_by_size[size].append(path)
        except OSError:
            # تجاهل الملفات التي لا يمكن الوصول إليها
            continue

    # الخطوة 2: للمجموعات ذات الحجم المتشابه، يتم حساب البصمة
    hashes = defaultdict(list)
    duplicate_groups = []

    # المرور فقط على الأحجام التي تحتوي على أكثر من ملف واحد
    for size, paths in files_by_size.items():
        if len(paths) > 1:
            for path in paths:
                file_hash = hash_file(path)
                if file_hash:
                    hashes[file_hash].append(path)

    # الخطوة 3: تجميع المجموعات النهائية التي لها نفس البصمة
    for file_hash, paths in hashes.items():
        if len(paths) > 1:
            duplicate_groups.append(paths)

    return duplicate_groups
