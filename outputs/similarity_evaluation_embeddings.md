# Evaluacion de similarity con sentence embeddings

## Configuracion

- Entrada: `data/intermediate/papers_master.csv`
- Gold positivo de referencia: `data/evaluation/similarity_gold.csv`
- Revision manual asistida: `data/evaluation/similarity_manual_review.csv`
- Texto usado: `abstract`
- Metrica: `cosine_similarity`
- Ranking: top 20 pares por modelo
- Modelo elegido para salida KG: `sentence-transformers/all-mpnet-base-v2`
- Modo offline/cache local: `true`
- Version local de sentence-transformers: `5.1.2`
- Etiquetas relevantes para precision@k: `similar`, `parcialmente similar`
- Revisiones exactas de modelos Hugging Face: pendiente fijar hash/revision para la entrega final

Modelos comparados:

- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/all-mpnet-base-v2`
- `sentence-transformers/paraphrase-MiniLM-L6-v2`

## Resultados

| Modelo | Pares revisados | Precision@k manual | Precision@k contra gold positivo |
|---|---:|---:|---:|
| `sentence-transformers/all-MiniLM-L6-v2` | 20/20 | 0.6000 | 0.3000 |
| `sentence-transformers/all-mpnet-base-v2` | 20/20 | 0.8500 | 0.5000 |
| `sentence-transformers/paraphrase-MiniLM-L6-v2` | 20/20 | 0.6500 | 0.3500 |

Con top 20, `sentence-transformers/all-mpnet-base-v2` obtiene la mejor precision@20 manual y se elige para alimentar el KG. El archivo `outputs/semantic_similarity_relations_embeddings.csv` conserva solo sus 17 pares aceptados como `similar` o `parcialmente similar`. La planilla `data/evaluation/similarity_manual_review.csv` conserva los 60 pares revisados para trazabilidad.

## Nota metodologica

Esta evaluacion compara modelos de sentence embeddings de Hugging Face sobre abstracts. Para cada modelo se calculan embeddings, cosine similarity entre todos los pares de papers y se exporta el top-k para revision manual asistida. La metrica usada para comparar modelos es precision@k manual: cada par se marca como `similar`, `parcialmente similar` o `no similar`; las dos primeras etiquetas cuentan como relevantes. La columna contra gold positivo es solo una referencia automatica inicial, porque el gold actual no contiene pares negativos exhaustivos.
