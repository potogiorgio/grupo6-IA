import csv
import os
import re
import argparse

INPUT_CSV = "data/intermediate/papers_master.csv"
OUTPUT_CSV = "outputs/paper_galaxies.csv"

# Common galaxy names and their potential Wikidata IDs (for later enrichment)
COMMON_GALAXIES = {
    "Milky Way": "Q2133",
    "Andromeda": "Q2469",
    "M31": "Q2469",
    "M33": "Q13724",
    "Triangulum": "Q13724",
    "Large Magellanic Cloud": "Q49957",
    "LMC": "Q49957",
    "Small Magellanic Cloud": "Q49963",
    "SMC": "Q49963",
    "Whirlpool": "Q13957",
    "M51": "Q13957",
    "Sombrero": "Q11084",
    "M104": "Q11084",
    "Centaurus A": "Q488130",
    "NGC 5128": "Q488130",
    "Pinwheel": "Q14371",
    "M101": "Q14371",
    "Black Eye": "Q13924",
    "M64": "Q13924",
    "Sunflower": "Q13940",
    "M63": "Q13940",
    "Cigar Galaxy": "Q11022",
    "M82": "Q11022",
    "Bode's Galaxy": "Q11014",
    "M81": "Q11014",
    "Cartwheel Galaxy": "Q632344",
    "Antennae Galaxies": "Q193632",
    "Tadpole Galaxy": "Q1341011",
}

# Regex for astronomical catalogs
CATALOG_PATTERNS = [
    r"\bM\s?\d{1,3}\b",
    r"\bNGC\s?\d{1,4}\b",
    r"\bIC\s?\d{1,4}\b",
    r"\bUGC\s?\d+\b",
    r"\bPGC\s?\d+\b",
]

def extract_galaxies(text):
    found = {}
    
    # Search for common names
    for name, wid in COMMON_GALAXIES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
            found[name] = {"wikidata_id": wid, "mention": name}
            
    # Search for catalog patterns
    for pattern in CATALOG_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            mention = match.group().strip()
            # Normalize mention (e.g., M 31 -> M31)
            normalized = re.sub(r"\s+", "", mention)
            if normalized not in found:
                found[normalized] = {"wikidata_id": "", "mention": mention}
                
    return found

def main():
    parser = argparse.ArgumentParser(description="Extract galaxies mentioned in papers")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        return

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    results = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper_id = row["id"]
            title = row["title"]
            abstract = row["abstract"]
            
            combined_text = title + " " + abstract
            galaxies = extract_galaxies(combined_text)
            
            for name, info in galaxies.items():
                results.append({
                    "paper_id": paper_id,
                    "galaxy_name": name,
                    "mention": info["mention"],
                    "wikidata_id": info["wikidata_id"],
                    "section": "title/abstract"
                })

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["paper_id", "galaxy_name", "mention", "wikidata_id", "section"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Extraction complete. Found {len(results)} galaxy mentions.")
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
