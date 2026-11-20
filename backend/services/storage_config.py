from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

CHROMA_DIR = BACKEND_DIR / "chroma_db"
SQLITE_DB_PATH = BACKEND_DIR / "sparse_index.db"
LIPI_MODEL_DIR = BACKEND_DIR / "models" / "lipi"