# run.py
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True, encoding="utf-8")

from app import create_app

import os

url = os.getenv("DATABASE_URL", "")
print("DATABASE_URL repr:", repr(url))
print("LEN:", len(url))
print("HEX:", [hex(ord(c)) for c in url])

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)