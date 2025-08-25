# Idempotent migration runner (called by install.sh if needed)
from app import settings
if __name__ == "__main__":
    settings.init_db()
    print("DB ready")
