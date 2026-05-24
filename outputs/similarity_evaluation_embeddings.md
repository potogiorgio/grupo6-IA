# Evaluacion de similarity con sentence embeddings

## Configuracion

- Entrada: `data/intermediate/papers_master.csv`
- Gold positivo de referencia: `data/evaluation/similarity_gold.csv`
- Revision manual asistida: `data/evaluation/similarity_manual_review.csv`
- Texto usado: `abstract`
- Metrica: `cosine_similarity`
- Ranking: top 10 pares por modelo
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
| `sentence-transformers/all-MiniLM-L6-v2` | 10/10 | 0.8000 | 0.5000 |
| `sentence-transformers/all-mpnet-base-v2` | 10/10 | 0.8000 | 0.4000 |
| `sentence-transformers/paraphrase-MiniLM-L6-v2` | 10/10 | 0.8000 | 0.5000 |

Los tres modelos empatan en precision@10 manual. Como criterio secundario, `sentence-transformers/all-MiniLM-L6-v2` se elige para la integracion final porque obtiene la misma precision@10 que los otros modelos con un modelo mas liviano. Si se prioriza capacidad del modelo por encima de costo computacional, `sentence-transformers/all-mpnet-base-v2` tambien queda defendible, pero no mejora la precision@10 en esta muestra.

El archivo `outputs/semantic_similarity_relations_embeddings.csv` conserva solo las relaciones aceptadas del modelo elegido para alimentar el KG: 8 pares marcados como `similar` o `parcialmente similar`. La planilla `data/evaluation/similarity_manual_review.csv` conserva los 30 pares revisados para trazabilidad de la comparacion.

## Nota metodologica

Esta evaluacion compara modelos de sentence embeddings de Hugging Face sobre abstracts. Para cada modelo se calculan embeddings, cosine similarity entre todos los pares de papers y se exporta el top-k para revision manual asistida. La metrica usada para comparar modelos es precision@k manual: cada par se marca como `similar`, `parcialmente similar` o `no similar`; las dos primeras etiquetas cuentan como relevantes. La columna contra gold positivo es solo una referencia automatica inicial, porque el gold actual no contiene pares negativos exhaustivos.
