import os
import time
import requests

def main():
    grobid_url = os.getenv("GROBID_URL", "http://localhost:8070/api/processFulltextDocument")
    base = grobid_url.split("/api/")[0].rstrip("/")

    probe = base  

    max_tries = int(os.getenv("GROBID_WAIT_TRIES", "240"))
    sleep_s = float(os.getenv("GROBID_WAIT_SLEEP", "2"))

    for i in range(1, max_tries + 1):
        try:
            r = requests.get(probe, timeout=3)
            if r.status_code in [200, 404]:
                print("Grobid listo ✅")
                return
        except Exception:
            pass

        print(f"Esperando a Grobid... ({i}/{max_tries})")
        time.sleep(sleep_s)

    raise SystemExit("ERROR: Grobid no respondió a tiempo")

if __name__ == "__main__":
    main()