import sqlite3, os, sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('file_archive.db')
cur = conn.cursor()
cur.execute("SELECT sha256, file_name, file_size, original_path FROM church_books WHERE file_name LIKE '%تجسد الكلمة%'")
for row in cur.fetchall():
    sha, fname, sz, p = row
    print(f"Name: {fname}")
    print(f"Size: {sz / (1024*1024):.2f} MB")
    print(f"Exists: {os.path.exists(p)}")
