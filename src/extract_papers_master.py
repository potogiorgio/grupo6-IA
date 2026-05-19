import os
import glob
import csv
import re
import xml.etree.ElementTree as ET

PAPERS_CSV = "data/papers.csv"
TEI_DIR = "data/tei"
OUT_CSV = "data/intermediate/papers_master.csv"

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def normalize_spaces(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def text_or_empty(node) -> str:
    if node is None:
        return ""
    return normalize_spaces("".join(node.itertext()))


def clean_title(title: str) -> str:
    return normalize_spaces(title)


def clean_abstract(abstract: str) -> str:
    abstract = normalize_spaces(abstract)
    abstract = re.sub(r"^(Abstract|ABSTRACT)\s*[:.]?\s*", "", abstract).strip()
    return abstract


def clean_acknowledgements(text: str) -> str:
    text = normalize_spaces(text)
    if not text:
        return ""

    text = re.sub(r"^(ACKNOWLEDGEMENTS|ACKNOWLEDGMENTS)\s*", "Acknowledgements. ", text)
    text = re.sub(r"^(Acknowledgements|Acknowledgments)\s*\.?", "Acknowledgements. ", text)

    return normalize_spaces(text)


def split_camel_case_name(name: str) -> str:
    if not name:
        return ""

    # NombreApellido -> Nommbre Apellido
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)

    # HJMo -> HJ Mo, SGVine -> SG Vine
    name = re.sub(r"\b([A-Z]{2,})([A-Z][a-z])", r"\1 \2", name)

    return normalize_spaces(name)

def clean_author_symbols(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"[^\w\s\-'.]", " ", text, flags=re.UNICODE)

    text = re.sub(r"\b\d+\b", " ", text)

    return normalize_spaces(text)


def clean_author_name(text: str) -> str:
    # Nos quedamos solo con el nombre
    text = normalize_spaces(text)
    if not text:
        return ""

    text = re.sub(r"\S+@\S+", "", text)

    cut_markers = [
        " Department ",
        " Dept. ",
        " Institute ",
        " Institut ",
        " University ",
        " Universidad ",
        " Observatory ",
        " Observatorio ",
        " Centre ",
        " Center ",
        " Faculty ",
        " School ",
        " Departamento ",
        " Astronomical ",
        " National ",
        " Chinese ",
        " European ",
        " Max-Planck",
        " Dipartimento ",
        " INFN ",
        " ESA ",
        " INAF ",
        " CSIC ",
    ]

    padded = f" {text} "
    positions = []

    for marker in cut_markers:
        pos = padded.find(marker)
        if pos != -1:
            positions.append(pos)

    if positions:
        text = padded[:min(positions)].strip()

    text = clean_author_symbols(text)
    text = split_camel_case_name(text)

    # Quitar restos numéricos al final
    text = re.sub(r"\s+\d[\d\s.,;:()±+-]*$", "", text)

    return normalize_spaces(text)


def extract_title(root) -> str:
    node = root.find(".//tei:titleStmt/tei:title", NS)
    return clean_title(text_or_empty(node))


def extract_abstract(root) -> str:
    node = root.find(".//tei:abstract", NS)
    return clean_abstract(text_or_empty(node))


def extract_authors(root) -> str:
    authors = []

    for author in root.findall(".//tei:sourceDesc//tei:author", NS):
        raw = text_or_empty(author)
        name = clean_author_name(raw)

        if name:
            authors.append(name)

    authors = list(dict.fromkeys(authors))
    return "; ".join(authors)


def extract_acknowledgements(root) -> str:
    texts = []

    # divs que GROBID marcó como acknowledgement
    ack_divs = root.findall(".//tei:div[@type='acknowledgement']", NS)

    if ack_divs:
        for div in ack_divs:
            txt = text_or_empty(div)
            if txt:
                texts.append(txt)

        return clean_acknowledgements(" ".join(texts))

    # si no hay type='acknowledgement', buscamos por el encabezado
    for div in root.findall(".//tei:div", NS):
        head = text_or_empty(div.find("tei:head", NS)).lower()

        if "acknowledg" in head:
            txt = text_or_empty(div)
            if txt:
                texts.append(txt)

    return clean_acknowledgements(" ".join(texts))


def parse_tei(xml_path: str) -> dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    paper_id = os.path.basename(xml_path).replace(".tei.xml", "")

    return {
        "id": paper_id,
        "title_extracted": extract_title(root),
        "abstract": extract_abstract(root),
        "authors": extract_authors(root),
        "acknowledgements": extract_acknowledgements(root),
    }


def read_papers_csv(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"id", "title", "doi", "openaire_url"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")

        return {row["id"]: row for row in reader}


def read_tei_records() -> dict:
    files = sorted(glob.glob(os.path.join(TEI_DIR, "*.xml")))

    if not files:
        print(f"AVISO: no encontré TEI XML en {TEI_DIR}")

    records = {}

    for path in files:
        try:
            row = parse_tei(path)
            records[row["id"]] = row
            print(f"OK TEI {row['id']}")
        except Exception as e:
            print(f"FAIL TEI {path}: {e}")

    return records


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def compute_notes(
    title_curated: str,
    title_extracted: str,
    abstract: str,
    authors: str,
    acknowledgements: str,
    has_pdf_url: bool,
    has_tei: bool,
) -> str:
    notes = []

    if not has_pdf_url:
        notes.append("missing_pdf_url")

    if not has_tei:
        notes.append("missing_tei")

    if not title_curated:
        notes.append("missing_curated_title")

    if not title_extracted:
        notes.append("missing_extracted_title")

    if not abstract:
        notes.append("missing_abstract")

    if not authors:
        notes.append("missing_authors")

    if not acknowledgements:
        notes.append("missing_acknowledgements")

    if len(acknowledgements) > 5000:
        notes.append("acknowledgements_may_be_noisy")

    lower_authors = authors.lower()
    if any(x in lower_authors for x in ["department", "institute", "university", "observatory"]):
        notes.append("authors_may_include_affiliations")

    return ";".join(notes)


def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

    papers = read_papers_csv(PAPERS_CSV)
    tei_records = read_tei_records()

    rows = []
    all_ids = sorted(set(papers.keys()) | set(tei_records.keys()))

    for paper_id in all_ids:
        p = papers.get(paper_id, {})
        t = tei_records.get(paper_id, {})

        title_curated = clean_title((p.get("title") or "").strip())
        title_extracted = clean_title((t.get("title_extracted") or "").strip())

        # Usamos el título curado del CSV base si existe, pq aveces no lo encuentra
        title = title_curated or title_extracted

        abstract = clean_abstract((t.get("abstract") or "").strip())
        authors = normalize_spaces((t.get("authors") or "").strip())
        acknowledgements = clean_acknowledgements((t.get("acknowledgements") or "").strip())

        pdf_url = (p.get("url") or p.get("pdf_url") or "").strip()

        has_abstract = bool(abstract)
        has_ack = bool(acknowledgements)
        has_tei = paper_id in tei_records

        usable_for_similarity = has_abstract
        usable_for_topic_modeling = has_abstract
        usable_for_ner = has_ack and len(acknowledgements) <= 5000

        notes = compute_notes(
            title_curated=title_curated,
            title_extracted=title_extracted,
            abstract=abstract,
            authors=authors,
            acknowledgements=acknowledgements,
            has_pdf_url=bool(pdf_url),
            has_tei=has_tei,
        )

        rows.append({
            "id": paper_id,
            "title": title,
            "doi": (p.get("doi") or "").strip(),
            "openaire_url": (p.get("openaire_url") or "").strip(),
            "pdf_url": pdf_url,
            "title_extracted": title_extracted,
            "abstract": abstract,
            "authors": authors,
            "acknowledgements": acknowledgements,
            "has_abstract": yes_no(has_abstract),
            "has_acknowledgements": yes_no(has_ack),
            "usable_for_similarity": yes_no(usable_for_similarity),
            "usable_for_topic_modeling": yes_no(usable_for_topic_modeling),
            "usable_for_ner": yes_no(usable_for_ner),
            "extraction_notes": notes,
        })

    fieldnames = [
        "id",
        "title",
        "doi",
        "openaire_url",
        "pdf_url",
        "title_extracted",
        "abstract",
        "authors",
        "acknowledgements",
        "has_abstract",
        "has_acknowledgements",
        "usable_for_similarity",
        "usable_for_topic_modeling",
        "usable_for_ner",
        "extraction_notes",
    ]

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Guardado: {OUT_CSV}")
    print(f"Papers totales: {len(rows)}")
    print(f"Con abstract: {sum(r['has_abstract'] == 'yes' for r in rows)}")
    print(f"Con acknowledgements: {sum(r['has_acknowledgements'] == 'yes' for r in rows)}")
    print(f"Usables para similarity: {sum(r['usable_for_similarity'] == 'yes' for r in rows)}")
    print(f"Usables para topic modeling: {sum(r['usable_for_topic_modeling'] == 'yes' for r in rows)}")
    print(f"Usables para NER: {sum(r['usable_for_ner'] == 'yes' for r in rows)}")

    problematic = [r for r in rows if r["extraction_notes"]]
    if problematic:
        print("\nPapers con notas:")
        for r in problematic:
            print(f"- {r['id']}: {r['extraction_notes']}")


if __name__ == "__main__":
    main()