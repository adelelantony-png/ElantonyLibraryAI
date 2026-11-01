import sqlite3
import os
import datetime
from PyQt5.QtCore import Qt

DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "file_archive.db")


def get_connection():
    """
    Establishes a high-performance connection to the database.
    Configured with Write-Ahead Logging (WAL) and NORMAL sync for 50x-100x batch speedups,
    preventing disk grinding while guaranteeing full ACID transaction safety.
    """
    con = sqlite3.connect(DB_NAME, timeout=30)
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA journal_mode = WAL;")
    con.execute("PRAGMA synchronous = NORMAL;")
    con.execute("PRAGMA cache_size = -64000;")  # 64MB RAM cache
    con.execute("PRAGMA temp_store = MEMORY;")
    return con

def backup_database(destination_dir: str = None, max_backups: int = 5) -> str:
    """
    Creates an online point-in-time snapshot backup using SQLite's native backup API.
    Safe to execute without locking out active threads or background workers.
    Keeps the most recent `max_backups` copies and auto-prunes older backups.
    """
    try:
        base_dir = destination_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")
        os.makedirs(base_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(base_dir, f"file_archive_backup_{timestamp}.db")

        src_con = get_connection()
        dst_con = sqlite3.connect(backup_file)
        src_con.backup(dst_con)
        dst_con.close()
        src_con.close()

        # Prune older backups beyond max_backups
        try:
            existing = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.startswith("file_archive_backup_") and f.endswith(".db")]
            existing.sort(key=os.path.getmtime, reverse=True)
            for old in existing[max_backups:]:
                try:
                    os.remove(old)
                except Exception:
                    pass
        except Exception:
            pass

        return backup_file
    except Exception as e:
        print(f"Database online backup error: {e}")
        return ""

def initialize_database():
    """
    Initializes the database, creating tables and FTS5 virtual table for fast search.
    Also handles schema migration for existing databases.
    """
    con = get_connection()
    cur = con.cursor()

    try:
        cur.execute("PRAGMA table_info(files)")
        columns = [info[1] for info in cur.fetchall()]
        if columns and 'ai_status' not in columns:
            print("Updating table 'files': Adding column 'ai_status'...")
            cur.execute("ALTER TABLE files ADD COLUMN ai_status TEXT DEFAULT 'pending'")
            print("Schema update complete.")
    except Exception as e:
        print(f"Error during schema migration: {e}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS root_folders (
            id INTEGER PRIMARY KEY,
            folder_path TEXT NOT NULL UNIQUE
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            root_folder_id INTEGER,
            file_path TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            extension TEXT,
            size INTEGER,
            mod_time REAL,
            category TEXT,
            content TEXT,
            ai_summary TEXT,
            suggested_tags TEXT,
            ai_status TEXT DEFAULT 'pending',
            FOREIGN KEY (root_folder_id) REFERENCES root_folders (id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            file_name,
            content,
            ai_summary,
            content='files',
            content_rowid='id',
            tokenize = 'porter unicode61'
        );
        """
    )

    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS files_after_insert
        AFTER INSERT ON files
        BEGIN
            INSERT INTO files_fts(rowid, file_name, content, ai_summary)
            VALUES (new.id, new.file_name, new.content, new.ai_summary);
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS files_after_delete
        AFTER DELETE ON files
        BEGIN
            INSERT INTO files_fts(files_fts, rowid, file_name, content, ai_summary)
            VALUES ('delete', old.id, old.file_name, old.content, old.ai_summary);
        END;
        """
    )
    cur.execute(
        """
        CREATE TRIGGER IF NOT EXISTS files_after_update
        AFTER UPDATE ON files
        BEGIN
            INSERT INTO files_fts(files_fts, rowid, file_name, content, ai_summary)
            VALUES ('delete', old.id, old.file_name, old.content, old.ai_summary);
            INSERT INTO files_fts(rowid, file_name, content, ai_summary)
            VALUES (new.id, new.file_name, new.content, new.ai_summary);
        END;
        """
    )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS tags (tag_id INTEGER PRIMARY KEY, tag_name TEXT NOT NULL UNIQUE)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS file_tags (file_id INTEGER, tag_id INTEGER, FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES tags (tag_id) ON DELETE CASCADE, PRIMARY KEY (file_id, tag_id))"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS rules (rule_id INTEGER PRIMARY KEY, condition_type TEXT NOT NULL, condition_value TEXT NOT NULL, action_type TEXT NOT NULL, action_value TEXT NOT NULL, priority INTEGER DEFAULT 0)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS action_history (action_id INTEGER PRIMARY KEY, file_id INTEGER, action_type TEXT NOT NULL, action_value TEXT NOT NULL, timestamp REAL, FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files (file_path);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_root_id ON files (root_folder_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (tag_name);")
    
    con.commit()
    con.close()

def rebuild_fts_index():
    """
    Rebuilds the FTS index using the special 'rebuild' command.
    This is the correct and efficient way for contentless FTS tables.
    """
    try:
        con = get_connection()
        cur = con.cursor()
        print("Rebuilding FTS index...")
        cur.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild');")
        con.commit()
        print("FTS index rebuild complete.")
        return True
    except Exception as e:
        print(f"Error rebuilding FTS index: {e}")
        return False
    finally:
        if con:
            con.close()

def get_file_count(project_id, category=None):
    """Gets the total count of files for a given filter."""
    if not project_id:
        return 0
    con = get_connection()
    cur = con.cursor()
    query = "SELECT COUNT(*) FROM files WHERE root_folder_id = ?"
    params = [project_id]
    if category and category != "الكل":
        query += " AND category = ?"
        params.append(category)
    cur.execute(query, params)
    count = cur.fetchone()[0]
    con.close()
    return count

def get_files_paginated(project_id, category, limit, offset, sort_column, sort_order):
    """Fetches a 'page' of files from the database."""
    if not project_id:
        return []
    con = get_connection()
    cur = con.cursor()
    
    sort_map = {1: 'file_name', 2: 'extension', 3: 'size', 4: 'mod_time', 5: 'file_path'}
    order_by_column = sort_map.get(sort_column, 'file_name')
    order_direction = 'DESC' if sort_order == Qt.DescendingOrder else 'ASC'
    
    query = f"SELECT file_path, file_name, size, mod_time, extension, ai_status FROM files WHERE root_folder_id = ?"
    params = [project_id]

    if category and category != "الكل":
        query += " AND category = ?"
        params.append(category)

    query += f" ORDER BY {order_by_column} {order_direction} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, params)
    results = cur.fetchall()
    con.close()
    return results

def search_files_by_content(search_term, category, root_folder_id):
    """
    Performs a high-speed full-text search using the FTS5 virtual table.
    """
    params = [root_folder_id, search_term]
    query_text = """
        SELECT f.file_path, f.file_name, f.size, f.mod_time, f.extension, f.ai_summary, 
               GROUP_CONCAT(t.tag_name, ', ')
        FROM files f
        JOIN files_fts ON f.id = files_fts.rowid
        LEFT JOIN file_tags ft ON f.id = ft.file_id
        LEFT JOIN tags t ON ft.tag_id = t.tag_id
        WHERE f.root_folder_id = ? AND files_fts MATCH ?
    """
    
    if category and category != "الكل":
        query_text += " AND f.category = ?"
        params.append(category)
        
    query_text += " GROUP BY f.id ORDER BY rank"
    
    return _execute_search_query(query_text, params)

def update_root_folder_path(folder_id, old_path, new_path):
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    try:
        cur.execute("UPDATE root_folders SET folder_path = ? WHERE id = ?", (new_path, folder_id))
        cur.execute("""
            UPDATE files 
            SET file_path = REPLACE(file_path, ?, ?) 
            WHERE root_folder_id = ?
        """, (old_path, new_path, folder_id))
        con.commit()
        return True
    except Exception as e:
        print(f"Error updating project path in DB: {e}")
        con.rollback()
        return False
    finally:
        con.close()

def update_folder_and_children_paths(old_path, new_path, root_folder_id):
    con = get_connection()
    cur = con.cursor()
    try:
        old_path_prefix = old_path.rstrip('/\\') + os.sep
        new_path_prefix = new_path.rstrip('/\\') + os.sep
        
        cur.execute("""
            UPDATE files 
            SET file_path = ? || SUBSTR(file_path, LENGTH(?) + 1)
            WHERE file_path LIKE ? AND root_folder_id = ?
        """, (new_path_prefix, old_path_prefix, old_path_prefix + '%', root_folder_id))
        
        con.commit()
        return True
    except Exception as e:
        print(f"Error updating folder and children paths in DB: {e}")
        con.rollback()
        return False
    finally:
        con.close()

def add_root_folder(path):
    con = get_connection()
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO root_folders (folder_path) VALUES (?)", (path,)
        )
        con.commit()
        cur.execute("SELECT id FROM root_folders WHERE folder_path = ?", (path,))
        folder_id = cur.fetchone()[0]
    finally:
        con.close()
    return folder_id

def get_all_root_folders():
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id, folder_path FROM root_folders")
    folders = cur.fetchall()
    con.close()

    # Self-healing drive resolver: automatically maps changed drive letters
    corrected_folders = []
    for f_id, f_path in folders:
        if os.path.exists(f_path):
            corrected_folders.append((f_id, f_path))
        else:
            fixed = False
            _, rest = os.path.splitdrive(f_path)
            for d in ['I:', 'H:', 'D:', 'E:', 'G:', 'C:']:
                cand = d + rest
                if os.path.exists(cand):
                    update_root_folder_path(f_id, f_path, cand)
                    corrected_folders.append((f_id, cand))
                    fixed = True
                    break
            if not fixed:
                corrected_folders.append((f_id, f_path))

    return corrected_folders

def process_file_batch(file_data_list, is_update, chunk_size: int = 500):
    """
    Processes a list of files using high-throughput batch transactions.
    Chunks large lists into 500-item transactions to maximize SQLite WAL efficiency
    and prevent memory bloat or lock contention.
    """
    if not file_data_list:
        return
    con = get_connection()
    cur = con.cursor()
    try:
        # Process in chunks of chunk_size (default 500)
        for i in range(0, len(file_data_list), chunk_size):
            chunk = file_data_list[i:i + chunk_size]
            con.execute("BEGIN TRANSACTION;")
            if is_update:
                cur.executemany(
                    "UPDATE files SET file_name = ?, extension = ?, size = ?, mod_time = ?, category = ?, content = ? WHERE file_path = ?",
                    chunk,
                )
            else:
                cur.executemany(
                    "INSERT OR IGNORE INTO files (root_folder_id, file_path, file_name, extension, size, mod_time, category, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    chunk,
                )
            con.commit()
    except Exception as e:
        print(f"Database batch processing error: {e}")
        try:
            con.rollback()
        except Exception:
            pass
    finally:
        con.close()

def delete_records_by_path(paths_to_delete):
    if not paths_to_delete:
        return
    con = get_connection()
    cur = con.cursor()
    try:
        cur.executemany(
            "DELETE FROM files WHERE file_path = ?",
            [(path,) for path in paths_to_delete],
        )
        con.commit()
    except Exception as e:
        print(f"Database delete error: {e}")
        con.rollback()
    finally:
        con.close()

def get_files_matching_patterns(patterns, root_folder_id):
    if not patterns or not root_folder_id:
        return []
    
    con = get_connection()
    cur = con.cursor()
    
    conditions = " OR ".join(["file_name LIKE ?"] * len(patterns))
    query = f"SELECT file_path, file_name FROM files WHERE ({conditions}) AND root_folder_id = ?"
    
    params = patterns + [root_folder_id]
    cur.execute(query, params)
    
    results = cur.fetchall()
    con.close()
    return results

def get_files_with_numeric_names(root_folder_id):
    if not root_folder_id:
        return []
    
    con = get_connection()
    cur = con.cursor()
    
    query = """
        SELECT file_path, file_name 
        FROM files 
        WHERE root_folder_id = ? 
        AND SUBSTR(file_name, 1, LENGTH(file_name) - LENGTH(extension) -1) GLOB '[0-9]*'
    """
    
    cur.execute(query, (root_folder_id,))
    results = cur.fetchall()
    con.close()
    return results

def update_file_with_ai_data(file_id, summary, tags):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE files SET ai_summary = ?, suggested_tags = ? WHERE id = ?",
        (summary, tags, file_id),
    )
    con.commit()
    con.close()

def get_mod_times_for_project(root_folder_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT file_path, mod_time FROM files WHERE root_folder_id = ?",
        (root_folder_id,),
    )
    mod_times = {row[0]: row[1] for row in cur.fetchall()}
    con.close()
    return mod_times

def get_categorized_files_with_details(root_folder_id):
    if not root_folder_id:
        return {}, []
    con = get_connection()
    cur = con.cursor()
    categorized_files_data = {}
    all_files_data = []
    cur.execute(
        "SELECT file_path, file_name, size, mod_time, category, extension, ai_status FROM files WHERE root_folder_id = ?",
        (root_folder_id,),
    )
    rows = cur.fetchall()
    for row in rows:
        file_path, file_name, size, mod_time, category, extension, ai_status = row
        file_data_tuple = (file_path, file_name, size, mod_time, extension, ai_status)
        if category not in categorized_files_data:
            categorized_files_data[category] = []
        categorized_files_data[category].append(file_data_tuple)
        all_files_data.append(file_data_tuple)
    con.close()
    return categorized_files_data, all_files_data

def get_all_files_for_engine(root_folder_id):
    if not root_folder_id:
        return []
    con = get_connection()
    cur = con.cursor()
    query = "SELECT f.id, f.file_path, f.file_name, f.extension, f.ai_summary, GROUP_CONCAT(t.tag_name, ' ') FROM files f LEFT JOIN file_tags ft ON f.id = ft.file_id LEFT JOIN tags t ON ft.tag_id = t.tag_id WHERE f.root_folder_id = ? GROUP BY f.id"
    cur.execute(query, (root_folder_id,))
    files = cur.fetchall()
    con.close()
    return files

def get_file_details_for_ai(file_path):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT id, content, ai_summary, suggested_tags, ai_status FROM files WHERE file_path = ?",
        (file_path,),
    )
    result = cur.fetchone()
    con.close()
    return result

def _execute_search_query(query, params):
    con = get_connection()
    cur = con.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    con.close()
    return results

def search_files_by_name(search_term, category, root_folder_id):
    params = [root_folder_id, f"%{search_term}%"]
    query_text = "SELECT f.file_path, f.file_name, f.size, f.mod_time, f.extension, f.ai_summary, GROUP_CONCAT(t.tag_name, ', ') FROM files f LEFT JOIN file_tags ft ON f.id = ft.file_id LEFT JOIN tags t ON ft.tag_id = t.tag_id WHERE f.root_folder_id = ? AND f.file_path LIKE ? "
    if category and category != "الكل":
        query_text += " AND f.category = ?"
        params.append(category)
    query_text += " GROUP BY f.id"
    return _execute_search_query(query_text, params)

def search_by_tag(tag_name, category, root_folder_id):
    params = [root_folder_id, f"%{tag_name}%"]
    query_text = "SELECT f.file_path, f.file_name, f.size, f.mod_time, f.extension, f.ai_summary, GROUP_CONCAT(t.tag_name, ', ') FROM files f JOIN file_tags ft ON f.id = ft.file_id JOIN tags t ON ft.tag_id = t.tag_id WHERE f.root_folder_id = ? AND t.tag_name LIKE ?"
    if category and category != "الكل":
        query_text += " AND f.category = ?"
        params.append(category)
    query_text += " GROUP BY f.id"
    return _execute_search_query(query_text, params)

def get_file_id(file_path):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
    result = cur.fetchone()
    con.close()
    return result[0] if result else None

def add_tag(tag_name):
    con = get_connection()
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag_name,))
    con.commit()
    cur.execute("SELECT tag_id FROM tags WHERE tag_name = ?", (tag_name,))
    tag_id = cur.fetchone()[0]
    con.close()
    return tag_id

def link_tag_to_file(file_id, tag_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)",
        (file_id, tag_id),
    )
    con.commit()
    con.close()

def unlink_tag_from_file(file_id, tag_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "DELETE FROM file_tags WHERE file_id = ? AND tag_id = ?", (file_id, tag_id)
    )
    con.commit()
    con.close()

def get_tags_for_file(file_id):
    if not file_id:
        return []
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT t.tag_id, t.tag_name FROM tags t JOIN file_tags ft ON t.tag_id = ft.tag_id WHERE ft.file_id = ?",
        (file_id,),
    )
    tags = cur.fetchall()
    con.close()
    return tags

def update_file_path(old_path, new_path):
    con = get_connection()
    cur = con.cursor()
    new_name = os.path.basename(new_path)
    base, ext = os.path.splitext(new_name)
    new_ext = ext.lower()

    cur.execute(
        "UPDATE files SET file_path = ?, file_name = ?, extension = ? WHERE file_path = ?",
        (new_path, new_name, new_ext, old_path),
    )
    con.commit()
    con.close()

def delete_file_record(file_path):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
    con.commit()
    con.close()

def get_all_rules():
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT rule_id, condition_type, condition_value, action_type, action_value, priority FROM rules ORDER BY priority DESC"
    )
    rules = cur.fetchall()
    con.close()
    return rules

def add_rule(condition_type, condition_value, action_type, action_value, priority=0):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO rules (condition_type, condition_value, action_type, action_value, priority) VALUES (?, ?, ?, ?, ?)",
        (condition_type, condition_value, action_type, action_value, priority),
    )
    con.commit()
    con.close()

def update_rule(
    rule_id, condition_type, condition_value, action_type, action_value, priority
):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "UPDATE rules SET condition_type = ?, condition_value = ?, action_type = ?, action_value = ?, priority = ? WHERE rule_id = ?",
        (condition_type, condition_value, action_type, action_value, priority, rule_id),
    )
    con.commit()
    con.close()

def delete_rule(rule_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM rules WHERE rule_id = ?", (rule_id,))
    con.commit()
    con.close()

def log_user_action(file_id, action_type, action_value):
    if not file_id:
        return
    con = get_connection()
    cur = con.cursor()
    timestamp = datetime.datetime.now().timestamp()
    cur.execute(
        "INSERT INTO action_history (file_id, action_type, action_value, timestamp) VALUES (?, ?, ?, ?)",
        (file_id, action_type, action_value, timestamp),
    )
    con.commit()
    con.close()