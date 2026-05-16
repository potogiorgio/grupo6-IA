import os
import glob
import argparse
import requests

GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8070/api/processFulltextDocument")

def process_pdf(pdf_path: str, out_dir: str, timeout: int = 600) -> str:
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(out_dir, f"{base}.tei.xml")

    with open(pdf_path, "rb") as f:
        files = {"input": (os.path.basename(pdf_path), f, "application/pdf")}
        data = {"consolidateHeader": "1", "consolidateCitations": "0"}
        r = requests.post(GROBID_URL, files=files, data=data, timeout=timeout)

    r.raise_for_status()
    with open(out_path, "wb") as out:
        out.write(r.content)

    return out_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf_dir", default="data/pdfs", help="Carpeta con PDFs")
    ap.add_argument("--out_dir", default="data/tei", help="Carpeta salida TEI XML")
    ap.add_argument("--limit", type=int, default=0, help="Procesar solo N PDFs (0 = todos)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    pdfs = sorted(glob.glob(os.path.join(args.pdf_dir, "*.pdf")))
    if args.limit and args.limit > 0:
        pdfs = pdfs[: args.limit]

    if not pdfs:
        print(f"No encontré PDFs en {args.pdf_dir}")
        return

    print(f"Procesando {len(pdfs)} PDFs con Grobid...")
    ok, fail = 0, 0

    for pdf in pdfs:
        try:
            out_path = process_pdf(pdf, args.out_dir)
            print(f"OK   {os.path.basename(pdf)} -> {os.path.basename(out_path)}")
            ok += 1
        except Exception as e:
            print(f"FAIL {os.path.basename(pdf)}: {e}")
            fail += 1

    print(f"\nResumen: OK={ok}, FAIL={fail}, TEI en {args.out_dir}")

    if fail > 0:
        raise SystemExit(2)

if __name__ == "__main__":
    main()