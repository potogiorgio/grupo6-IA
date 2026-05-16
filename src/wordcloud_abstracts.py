import os
import glob
import re
import xml.etree.ElementTree as ET
from collections import Counter

from wordcloud import WordCloud
import matplotlib.pyplot as plt

TEI_DIR = "data/tei"
OUT_DIR = "outputs"

STOPWORDS = {
    "the","and","to","of","in","a","for","is","on","we","this","that","with","as","are",
    "our","be","by","an","from","it","or","at","can","also","these","such","using",
    "into","their","than","more","may","not","have","has","been","which","will","were"
}

def extract_abstract(xml_path: str) -> str:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    abs_node = root.find(".//tei:abstract", ns)
    if abs_node is None:
        return ""
    return " ".join("".join(abs_node.itertext()).split())

def clean_and_tokenize(text: str):
    # solo letras, bajar a minúsculas
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    tokens = [t for t in text.split() if len(t) >= 3 and t not in STOPWORDS]
    return tokens

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    files = sorted(glob.glob(os.path.join(TEI_DIR, "*.xml")))
    if not files:
        print(f"No encontré TEI XML en {TEI_DIR}. ¿Corriste el script de Grobid?")
        return

    abstracts = []
    missing = 0
    for f in files:
        ab = extract_abstract(f)
        if ab:
            abstracts.append(ab)
        else:
            missing += 1

    all_text = "\n".join(abstracts)
    tokens = clean_and_tokenize(all_text)

    if not tokens:
        print("No pude extraer tokens del texto. ¿Los abstracts están vacíos?")
        return

    # Guardamos top palabras
    counts = Counter(tokens)
    top_path = os.path.join(OUT_DIR, "abstract_keywords_top50.txt")
    with open(top_path, "w", encoding="utf-8") as w:
        for word, c in counts.most_common(50):
            w.write(f"{word}\t{c}\n")

    wc = WordCloud(
        width=1400,
        height=800,
        background_color="white",
        collocations=False, 
    ).generate(" ".join(tokens))

    out_img = os.path.join(OUT_DIR, "wordcloud_abstracts.png")
    plt.figure(figsize=(14, 8))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_img, dpi=200)
    plt.close()

    print(f"OK Wordcloud generado: {out_img}")
    print(f"OK Top 50 keywords: {top_path}")
    print(f"Abstracts encontrados: {len(abstracts)} / {len(files)} (sin abstract: {missing})")

if __name__ == "__main__":
    main()