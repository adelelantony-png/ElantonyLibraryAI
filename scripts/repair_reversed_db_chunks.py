import sqlite3
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

REVERSED_INDICATORS = [
    "سيدقلا", "هللا", "يسلا", "سويسانث", "سيلريك", "مساب", "ىلإ", "ىلع", "ىتلا", "ىذلا",
    "داسفلا", "سداسلا", "عباسلا", "سماخلا", "عبارلا", "ثلاثلا", "يناثلا", "لوألا", "لصفلا",
    "ىرشبلا", "سنجلا", "ةملكلا", "ةقيلخلا", "ةعيرشلا", "ةروص", "ةسدنكلا", "ةسردمل", "ةياغل"
]

def is_line_reversed(line: str) -> bool:
    tokens = line.strip().split()
    if not tokens:
        return False
    score = 0
    for t in tokens:
        if t.startswith('ة') and len(t) > 1:
            score += 2
        if t.startswith('اً') and len(t) > 1:
            score += 2
        if t in REVERSED_INDICATORS:
            score += 2
        if t.endswith('لا') and len(t) > 3 and not t.startswith('ال'):
            score += 1
    return score >= 2

def repair_arabic_text(text: str) -> str:
    lines = text.split("\n")
    repaired_lines = []
    has_change = False
    for l in lines:
        if is_line_reversed(l):
            repaired_lines.append(l[::-1])
            has_change = True
        else:
            repaired_lines.append(l)
    return "\n".join(repaired_lines), has_change

for db_path in [r'D:\Prog\ArchiveMasterFinal\file_archive.db', r'I:\2021\2020\✠ Cross Coptic Library ✠\ArchiveMaster\file_archive.db']:
    print(f"\nProcessing database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT rowid, chunk_text FROM church_chunks_fts")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Total chunks: {total:,}. Scanning for reversed text...")

    updates = []
    for r in rows:
        rowid = r[0]
        text = r[1]
        if not text:
            continue
        repaired, changed = repair_arabic_text(text)
        if changed:
            updates.append((repaired, rowid))

    print(f"Found {len(updates):,} chunks needing reversal repair.")

    if updates:
        print("Executing batch update in FTS5...")
        cur.executemany("UPDATE church_chunks_fts SET chunk_text = ? WHERE rowid = ?", updates)
        conn.commit()
        print("Batch update committed successfully!")

    conn.close()

print("\nRepair completed on both databases!")
