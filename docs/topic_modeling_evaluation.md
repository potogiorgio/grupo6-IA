# Selección y justificación del modelo BERTopic

## Objetivo

El objetivo de la tarea de topic modeling es identificar automáticamente temas comunes dentro de un corpus de 30 publicaciones científicas relacionadas con Astrophysics of Galaxies. Los topics extraídos se integrarán posteriormente en el Knowledge Graph como relaciones semánticas entre papers y áreas temáticas.

El proceso de topic modeling se realiza sobre los abstracts extraídos automáticamente de los papers mediante GROBID y almacenados en `papers_master.csv`.

---

# Por qué se seleccionó BERTopic

Para este proyecto se seleccionó BERTopic como framework principal de topic modeling.

BERTopic es una técnica moderna de topic modeling basada en embeddings semánticos y clustering. A diferencia de métodos tradicionales como LDA (Latent Dirichlet Allocation), BERTopic utiliza embeddings generados por modelos transformer, permitiendo capturar mejor la similitud semántica entre textos científicos.

Esto es especialmente importante en literatura científica, donde diferentes artículos pueden hablar de conceptos similares utilizando terminología distinta.

Por ejemplo:

- "stellar halo"
- "galactic halo"
- "halo structure"

Métodos tradicionales basados únicamente en frecuencia de palabras pueden tratar estos términos como conceptos distintos, mientras que los embeddings semánticos son capaces de detectar que están relacionados semánticamente.

Debido a esto, BERTopic resulta más adecuado para corpus científicos pequeños y especializados como el utilizado en este proyecto.

---

# Modelo de embeddings utilizado

El modelo de embeddings utilizado fue:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Este modelo pertenece a la librería Sentence Transformers y genera embeddings semánticos densos para frases y documentos completos.

El modelo fue seleccionado porque:

Es ligero y computacionalmente eficiente.
Tiene buen rendimiento en tareas de similitud semántica.
Es ampliamente utilizado en NLP.
Funciona correctamente sobre corpus pequeños y medianos.
Es totalmente compatible con BERTopic.

Además, el mismo modelo fue reutilizado para calcular la similitud semántica entre papers, manteniendo consistencia dentro del pipeline del proyecto.

---

# Pipeline de BERTopic

El proceso de topic modeling está compuesto por varias etapas.

## 1. Extracción de abstracts

Los abstracts fueron extraídos desde los PDFs mediante GROBID y almacenados en:

data/intermediate/papers_master.csv

Solo se utilizaron papers marcados como válidos para topic modeling.

## 2. Generación de embeddings

Cada abstract fue transformado en un embedding semántico utilizando:

sentence-transformers/all-MiniLM-L6-v2

Estos embeddings representan el significado semántico de cada abstract dentro de un espacio vectorial de alta dimensión.

## 3. Reducción de dimensionalidad con UMAP

BERTopic utiliza internamente UMAP (Uniform Manifold Approximation and Projection) para reducir la dimensionalidad de los embeddings antes del clustering.

Se utilizaron los siguientes parámetros:

UMAP(
    n_neighbors=5,
    n_components=2,
    min_dist=0.0,
    metric="cosine",
    random_state=42
)

UMAP fue seleccionado porque permite preservar relaciones semánticas entre documentos mientras reduce la complejidad computacional.

## 4. Clustering con HDBSCAN

Tras reducir la dimensionalidad, los abstracts fueron agrupados mediante HDBSCAN.

Se utilizaron los siguientes parámetros:

HDBSCAN(
    min_cluster_size=3,
    min_samples=1,
    metric="euclidean",
    prediction_data=True
)

HDBSCAN fue seleccionado porque:

Determina automáticamente el número de clusters.
Maneja correctamente ruido y outliers.
Funciona bien sobre datasets pequeños.
Es uno de los métodos recomendados por BERTopic.

Los documentos asignados al Topic -1 son considerados outliers o documentos sin una asignación clara a un topic.

## 5. Representación de topics

BERTopic genera automáticamente:

palabras representativas por topic,
documentos representativos,
asignaciones paper-topic.

Los topics se exportan a:

data/intermediate/topics_info.csv

Las asignaciones paper-topic se exportan a:

data/intermediate/paper_topics.csv

---

# Selección del threshold

Se utilizó un threshold de probabilidad de:

0.60

para determinar si un paper pertenece de forma suficientemente fuerte a un topic.

Este threshold evita asignaciones débiles o ambiguas.

Cada relación topic-paper almacena:
topic asignado,
probabilidad,
threshold utilizado,
modelo de embeddings,
framework de topic modeling.

Esto mejora la transparencia y reproducibilidad del Knowledge Graph.

---

# Por qué BERTopic en lugar de LDA

Modelos tradicionales como LDA se basan principalmente en frecuencias de palabras y representaciones bag-of-words.

Sin embargo, los abstracts científicos contienen:
- terminología especializada,
- sinónimos,
- conceptos semánticamente relacionados expresados de formas diferentes.

Por ello, los embeddings semánticos proporcionan representaciones más robustas que los métodos puramente léxicos.

BERTopic fue preferido porque:
- captura similitud semántica,
- funciona correctamente con corpus pequeños,
- utiliza modelos transformer modernos,
produce topics interpretables.

---

# Limitaciones

Algunas limitaciones de BERTopic en este proyecto son:

- El corpus contiene únicamente 30 papers.
- Existen documentos clasificados como outliers (Topic -1).
- La interpretación de topics requiere validación humana.
- Los resultados dependen parcialmente de los parámetros de clustering utilizados.

A pesar de estas limitaciones, BERTopic permitió generar topics coherentes e interpretables adecuados para su integración en el Knowledge Graph final.

---

# Resultados obtenidos

El modelo BERTopic logró identificar correctamente varios grupos temáticos dentro del corpus de 30 papers científicos utilizados en el proyecto.

En total, el modelo generó:

- 5 topics principales.
- 1 grupo de outliers (`Topic -1`).

Los topics detectados representan diferentes áreas de investigación relacionadas con astrofísica de galaxias, incluyendo:

- dinámica de galaxias espirales,
- halos estelares,
- composición química estelar,
- interacción entre galaxias,
- formación estelar y gas molecular.

Los resultados obtenidos muestran que BERTopic fue capaz de agrupar papers semánticamente relacionados incluso cuando utilizaban terminología distinta.

---

# Análisis de outliers

BERTopic clasifica como `Topic -1` aquellos documentos que no pertenecen claramente a ningún cluster temático.

En este proyecto:
- Total de papers: 30
- Papers clasificados como outliers: 2

Esto representa aproximadamente un 6.67% del corpus total.
Un porcentaje bajo de outliers indica que la mayoría de abstracts presentan relaciones semánticas suficientemente claras para ser agrupadas en topics coherentes.
Los documentos clasificados como outliers probablemente corresponden a papers muy específicos o con contenido híbrido difícil de asociar a un único topic.

---

# Coherencia de topics

La coherencia de los topics fue evaluada manualmente utilizando:
- las palabras representativas generadas por BERTopic,
- los documentos representativos de cada cluster,
- la inspección de abstracts individuales.

Los topics generados mostraron una coherencia temática razonable y consistente con el dominio científico del corpus.

Por ejemplo:

| Topic | Interpretación aproximada |
|---|---|
| Topic 0 | estructura y dinámica galáctica |
| Topic 1 | composición química y poblaciones estelares |
| Topic 2 | interacción entre galaxias y formación estelar |
| Topic 3 | fenómenos energéticos y rayos cósmicos |
| Topic 4 | observaciones astronómicas específicas |

---

# Validación manual (gold data)

Con el objetivo de validar los resultados del topic modeling, se realizó una inspección manual sobre una muestra representativa de papers.

Para cada paper se revisó:

- el abstract original,
- el topic asignado,
- las palabras representativas del cluster.

Esta validación permitió comprobar que la mayoría de asignaciones realizadas por BERTopic eran coherentes con el contenido científico de los abstracts.