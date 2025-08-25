"""
Idempotent DB migration/initialization.

Run as:
  python -m db.migrations     (preferred, from repo root)
or:
  python db/migrations.py     (also works now)
"""
from pathlib import Path
import sys

# Ensure project root is on sys.path when run directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import settings  # now safe either way

if __name__ == "__main__":
    settings.init_db()
    print("DB ready")
