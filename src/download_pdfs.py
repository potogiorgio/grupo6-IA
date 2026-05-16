import csv
import os
import sys
import urllib.request
from urllib.error import URLError, HTTPError

CSV_PATH = os.path.join("data", "papers.csv")
OUT_DIR = os.path.join("data", "pdfs")

def safe_makedirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def download(url: str, out_path: str) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (paper-downloader)"},
    )
    with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
        f.write(resp.read())

def main() -> int:
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: no existe {CSV_PATH}")
        return 1

    safe_makedirs(OUT_DIR)

    ok, fail = 0, 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"id", "url"}
        if not required.issubset(set(reader.fieldnames or [])):
            print(f"ERROR: {CSV_PATH} debe tener columnas: {sorted(required)}")
            print(f"Columnas actuales: {reader.fieldnames}")
            return 1

        for row in reader:
            paper_id = (row.get("id") or "").strip()
            url = (row.get("url") or "").strip()
            if not paper_id or not url:
                continue

            out_path = os.path.join(OUT_DIR, f"{paper_id}.pdf")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                print(f"SKIP  {paper_id} (ya existe)")
                ok += 1
                continue

            try:
                print(f"DOWN  {paper_id} <- {url}")
                download(url, out_path)
                if os.path.getsize(out_path) == 0:
                    raise RuntimeError("archivo descargado vacío")
                ok += 1
            except (HTTPError, URLError, RuntimeError, Exception) as e:
                print(f"FAIL  {paper_id}: {e}")
                fail += 1
                try:
                    if os.path.exists(out_path):
                        os.remove(out_path)
                except Exception:
                    pass

    print(f"\nResumen: OK={ok}, FAIL={fail}, carpeta={OUT_DIR}")
    return 0 if fail == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())