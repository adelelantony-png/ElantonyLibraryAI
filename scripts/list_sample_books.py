import sqlite3, sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('file_archive.db')
cur = conn.cursor()
cur.execute("SELECT sha256, file_name, page_count FROM church_books WHERE is_duplicate_of IS NULL LIMIT 25")
for row in cur.fetchall():
    sha, fname, p = row
    print(f"sha={sha[:8]} | pages={p} | {fname}")
