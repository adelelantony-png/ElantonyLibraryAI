# -*- coding: utf-8 -*-
"""
Database Metadata and Classification Sanitization:
1. Distinguishes Bishop Gregorios (20th c.) from St. Gregory the Theologian (4th c.).
2. Classifies James Anas Protestant theology books as Tier 5 (Protestant/Comparative).
3. Corrects Dr. Maurice Tawadros books to author 'الدكتور موريس تاوضروس (أستاذ اللاهوت العقيدي)'.
"""

import sys
sys.path.insert(0, r"D:\Prog\ArchiveMasterFinal")

from elantony.database.connection import get_connection

def sanitize_database():
    conn = get_connection()
    cur = conn.cursor()

    print("--- 1. Fixing Protestant 'كتاب علم اللاهوت العقيدي' (James Anas) ---")
    cur.execute("""
        UPDATE church_books 
        SET author = 'القس جيمس أنس (لاهوت بروتستانتي)', 
            authenticity_tier = 5,
            source_types = '["COMPARATIVE_THEOLOGY", "NON_ORTHODOX"]'
        WHERE file_name LIKE 'كتاب علم اللاهوت العقيدي%'
    """)
    p_books = cur.rowcount
    print(f"Updated {p_books} Protestant books to Tier 5.")

    print("\n--- 2. Fixing Dr. Maurice Tawadros 'علم اللاهوت العقيدي' ---")
    cur.execute("""
        UPDATE church_books 
        SET author = 'الدكتور موريس تاوضروس (أستاذ اللاهوت العقيدي)',
            authenticity_tier = 3,
            source_types = '["THEOLOGICAL_STUDIES", "ACADEMIC_STUDIES"]'
        WHERE file_name LIKE '%موريس تاوضروس%'
    """)
    m_books = cur.rowcount
    print(f"Updated {m_books} Dr. Maurice Tawadros books.")

    print("\n--- 3. Fixing Bishop Gregorios (الأنبا غريغوريوس) ---")
    cur.execute("""
        UPDATE church_books 
        SET author = 'الأنبا غريغوريوس (أسقف البحث العلمي)',
            authenticity_tier = 3,
            source_types = '["THEOLOGICAL_STUDIES", "ACADEMIC_STUDIES"]'
        WHERE (file_name LIKE '%أنبا%غريغوريوس%' OR file_name LIKE '%انبا%غريغوريوس%' OR file_name LIKE '%موسوعة_الأنبا_غريغوريوس%')
          AND file_name NOT LIKE '%النزينزي%'
          AND file_name NOT LIKE '%النيصي%'
          AND file_name NOT LIKE '%الناطق بالالهيات%'
    """)
    g_books = cur.rowcount
    print(f"Updated {g_books} Anba Gregorios books to 'الأنبا غريغوريوس (أسقف البحث العلمي)' (Tier 3).")

    print("\n--- 4. Verify St. Gregory the Theologian (4th c.) Works ---")
    cur.execute("""
        UPDATE church_books 
        SET author = 'القديس غريغوريوس اللاهوتي',
            authenticity_tier = 1,
            source_types = '["PRIMARY_PATRISTIC"]'
        WHERE file_name LIKE '%النزينزي%' 
           OR file_name LIKE '%الخطب اللاهوتية%' 
           OR file_name LIKE '%الناطق بالالهيات%'
    """)
    naz_books = cur.rowcount
    print(f"Updated {naz_books} genuine 4th-c. Gregory of Nazianzus books to Tier 1.")

    conn.commit()
    conn.close()
    print("\nSanitization successfully completed!")

if __name__ == "__main__":
    sanitize_database()
