import os
import glob
import xml.etree.ElementTree as ET

TEI_DIR = "data/tei"
OUT_DIR = "outputs"

def extract_links(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    refs = root.findall(".//tei:ref", ns)

    links = []

    for r in refs:
        target = r.attrib.get("target")
        if is_external_link(target):
            links.append(target)

    # eliminar duplicados 
    links = list(dict.fromkeys(links))

    return links

def is_external_link(target: str) -> bool:
    if not target:
        return False
    t = target.strip().lower()
    # descartamos anchors internos
    if t.startswith("#"):
        return False
    # aceptamos links web y otros esquemas comunes
    return t.startswith("http://") or t.startswith("https://") or t.startswith("doi:") or t.startswith("arxiv:")

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    files = sorted(glob.glob(os.path.join(TEI_DIR, "*.xml")))

    out_file = os.path.join(OUT_DIR, "links_per_paper.txt")

    with open(out_file, "w", encoding="utf-8") as f:
        for file in files:
            paper = os.path.basename(file).replace(".tei.xml", "")
            links = extract_links(file)

            f.write(f"\n--- {paper} ---\n")

            if links:
                for link in links:
                    f.write(link + "\n")
            else:
                f.write("No links found\n")

            print(f"{paper}: {len(links)} links")

    print(f"\nArchivo guardado en: {out_file}")

if __name__ == "__main__":
    main()