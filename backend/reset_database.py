import sqlite3
import shutil
from pathlib import Path
import chromadb

BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "sparse_index.db"
CHROMA_DIR = BACKEND_DIR / "chroma_db"
DOWNLOADS_DIR = BACKEND_DIR / "downloads"
ROOT_CHROMA_DIR = BACKEND_DIR.parent / "chroma_db"

print("=" * 60)
print("RESETTING COURSEPILOT DATA")
print("=" * 60)

# 1. Clear SQLite tables
if DB_PATH.exists():
    print("\n1. Clearing SQLite database tables...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    for table in ["courses", "course_videos", "sparse_postings", "bge_m3_index_state"]:
        if table in tables:
            cursor.execute(f"DELETE FROM {table}")
            print(f"   ✓ Emptied table: {table}")
    
    # Reset autoincrement ID counter
    if "sqlite_sequence" in tables:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('courses')")
    
    conn.commit()
    cursor.execute("VACUUM")
    conn.close()

# 2. Reset ChromaDB collection
print("\n2. Clearing ChromaDB vector store...")
if CHROMA_DIR.exists():
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        for col in client.list_collections():
            client.delete_collection(col.name)
            print(f"   ✓ Deleted collection: {col.name}")
    except Exception as e:
        print(f"   Notice clearing Chroma: {e}")

# 3. Remove duplicate root chroma folder
if ROOT_CHROMA_DIR.exists():
    shutil.rmtree(ROOT_CHROMA_DIR, ignore_errors=True)
    print("\n3. Removed duplicate root chroma_db folder.")

# 4. Clean up any leftover downloaded mp3s
print("\n4. Cleaning audio download files...")
if DOWNLOADS_DIR.exists():
    for f in DOWNLOADS_DIR.glob("*.mp3"):
        f.unlink()
        print(f"   ✓ Deleted: {f.name}")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE! Your CoursePilot backend is now completely fresh.")
print("=" * 60)