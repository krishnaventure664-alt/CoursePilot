import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

CHROMA_DIR = BACKEND_DIR / "chroma_db"
SQLITE_DB_PATH = BACKEND_DIR / "sparse_index.db"
SEED_DB_PATH = BACKEND_DIR / "sparse_index_seed.db"
LIPI_MODEL_DIR = BACKEND_DIR / "models" / "lipi"

# Auto-seed SQLite database on fresh cloud deployments (e.g. Render)
if not SQLITE_DB_PATH.exists() and SEED_DB_PATH.exists():
    try:
        shutil.copy2(SEED_DB_PATH, SQLITE_DB_PATH)
    except Exception:
        pass
