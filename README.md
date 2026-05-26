# Open Science and AI in Research Software Engineering - Grupo 6

Este es el repositorio del **Grupo 6**.

El objetivo es crear un **grafo de conocimiento** de publicaciones científicas en el ámbito de **Astrophysics of Galaxies**.

## Integrantes

- Michele Barrera Colmenares
- Jorge Blanco Carrasco
- Maria Agostina Squillari
- Andrés Pecker Matesanz

---

## Declaración de uso de IA

Durante el desarrollo del proyecto se ha utilizado IA generativa como apoyo para tareas de asistencia técnica, depuración, redacción y organización del código y la documentación.

En concreto, se ha utilizado para:

- obtener ayuda en la implementación de scripts Python;
- depurar errores de ejecución;
- mejorar la estructura del README;
- apoyar la redacción de explicaciones sobre Topics, Similiraty, NER, ROR, provenance y RO-Crate;
- revisar y mejorar partes del pipeline.

Todas las decisiones técnicas finales, la ejecución de los scripts, la validación de resultados, la selección de modelos y la integración en el Knowledge Graph han sido revisadas y realizadas por los miembros del grupo.

El uso de IA generativa no sustituye la evaluación experimental del proyecto. Los resultados incluidos en el repositorio proceden de la ejecución de la pipeline sobre el corpus seleccionado y se validan mediante los scripts incluidos en el repositorio.

---

## 1. Objetivo

El objetivo del proyecto es realizar un análisis avanzado de publicaciones científicas mediante técnicas de Open Science, NLP y Knowledge Graphs.

El sistema permite:

- procesar papers científicos en PDF;
- extraer metadatos, autores, abstracts y acknowledgements;
- agrupar papers por topics;
- calcular similitud semántica entre papers;
- identificar galaxias estudiadas en cada paper;
- extraer personas, organizaciones, financiadores y grants desde acknowledgements;
- enriquecer organizaciones mediante ROR;
- construir un Knowledge Graph RDF con relaciones n-arias y umbrales;
- validar el KG y su provenance;
- consumir el KG mediante consultas SPARQL y una demo visual.

## 2. Caso de uso

El KG permitirá responder preguntas como:

- **¿Qué papers estudian una misma galaxia?** Permite agrupar conocimiento sobre objetos astronómicos específicos (ej. M31, Vía Láctea).
- **¿Qué papers son similares por su abstract aunque no estudien exactamente el mismo objeto?** Ayuda a encontrar metodologías o modelos teóricos aplicables a diferentes galaxias.
- **¿Qué autores e instituciones trabajan sobre las mismas galaxias o temas?** Facilita la identificación de redes de colaboración y centros de experiencia en subcampos específicos de la astrofísica. Por ejemplo, permite ver qué grupos de investigación dominan el estudio de la dinámica de galaxias espirales.
- **¿Qué organizaciones financian investigación sobre determinados objetos astronómicos?** Permite analizar el impacto de la financiación en el descubrimiento y estudio de objetos celestes.
- **¿Qué topics emergen en el corpus y qué papers pertenecen a cada topic?** Facilita la exploración temática del dominio.

### Ejemplos de Scores y Relaciones

- **Topic Score:** Representa la fuerza de pertenencia de un paper a un topic (probabilidad). Ejemplo: Un paper sobre "rotación galáctica" puede tener un `topicScore` de 0.85 para el Topic 0 (dinámica) y un `threshold` de 0.60.
- **Similarity Score:** Cuantifica la similitud semántica entre dos papers basada en sus abstracts. Ejemplo: El Paper A y el Paper B tienen un `similarityScore` de 0.92, indicando que tratan temas casi idénticos, permitiendo al investigador saltar de una lectura a otra relacionada.

---

## 3. Fuentes de datos

### OpenAIRE

OpenAIRE se utiliza como fuente principal para recuperar publicaciones científicas del dominio seleccionado, junto con metadatos principales y enlaces a los PDFs. **No se utiliza la API de ArXiv directamente**, sino que se aprovecha la agregación de OpenAIRE.

### ROR

ROR se utiliza para enriquecer organizaciones detectadas en acknowledgements. El script `src/enrich_organizations_ror.py` consulta la API de ROR y genera un fichero de correspondencias con identificadores persistentes de organizaciones.

### Wikidata

Se utiliza Wikidata para:
1.  Obtener identificadores persistentes de las galaxias detectadas.
2.  Normalizar nombres de objetos astronómicos y obtener metadatos adicionales como el tipo de galaxia.
3.  Vincular autores y organizaciones con sus perfiles globales cuando están disponibles.

---

## 4. Estructura del repositorio

```text
data/
├── intermediate/
│   └── papers_master.csv
└── evaluation/
    └── ner/
        ├── ner_gold.csv
        └── ner_model_comparison.csv

outputs/
├── kg.ttl
├── funding_entities.csv
├── organization_ror_matches.csv
├── semantic_similarity_relations_embeddings.csv
├── paper_topics.csv
├── topics_info.csv
├── paper_galaxies.csv
├── provenance.json
└── provenance.ttl

src/
├── download_pdfs.py
├── run_grobid.py
├── extract_papers_master.py
├── generate_similarity.py
├── generate_topics.py
├── extract_galaxies.py
├── funding.py
├── enrich_organizations_ror.py
├── build_kg.py
├── validate_kg.py
├── generate_provenance.py
├── generate_rocrate.py
└── run_sparql_queries.py

demo/
└── app.py

ontologia/
└── ontology.ttl

ro-crate-metadata.json
requirements.txt
docker-compose.yml
Dockerfile
README.md
```

---

## 5. Instalación

Crear y activar entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## 6. Pipeline completa de ejecución

### 6.1. Ejecución con Docker (Recomendado)

El proyecto está totalmente dockerizado para facilitar su ejecución.

**Iniciar GROBID y procesar todo el pipeline:**
Este comando descarga PDFs, extrae texto, ejecuta modelos de IA y construye el KG.
```bash
docker compose run --rm pipeline
```

**Levantar la Web App (Demo):**
```bash
docker compose up demo
```
Luego accede a `http://localhost:8501`.

---

### 6.2. Ejecución Manual (Local)

#### A. Iniciar GROBID
```bash
docker compose up -d grobid
```

#### B. Pipeline de procesamiento
```bash
# 1. Descargar PDFs
python src/download_pdfs.py

# 2. Procesar con GROBID
python src/run_grobid.py --limit 0

# 3. Generar CSV maestro
python src/extract_papers_master.py

# 4. Análisis de IA (Similitud y Topics)
python src/generate_similarity.py --allow-download
python src/generate_topics.py --allow-download

# 5. Extracción de Galaxias
python src/extract_galaxies.py

# 6. NER y Funding
python src/funding.py --allow-download
python src/enrich_organizations_ror.py

# 7. Construcción del Knowledge Graph
python src/build_kg.py \
  --similarity outputs/semantic_similarity_relations_embeddings.csv \
  --topics outputs/paper_topics.csv \
  --funding outputs/funding_entities.csv \
  --galaxies outputs/paper_galaxies.csv \
  --ror outputs/organization_ror_matches.csv

# 8. Metadatos y Validación
python src/generate_provenance.py
python src/generate_rocrate.py
python src/validate_kg.py
```

---
## 7. Demo Streamlit

La demo interactiva permite consumir el Knowledge Graph de forma visual y técnica.

**Características principales:**
- **Explorador de Papers:** Detalle de autores, topics, similitudes y galaxias estudiadas.
- **Consola SPARQL:** Permite ejecutar consultas personalizadas directamente sobre el KG.
- **Visualización de Umbrales:** Muestra los scores de IA junto a sus umbrales de corte (thresholds).
- **Rankings:** Estadísticas de las galaxias y organizaciones más mencionadas.

Ejecutar localmente:
```bash
streamlit run demo/app.py
```

---

## 8. Outputs principales

Los principales resultados generados por la pipeline son:

```text
data/intermediate/papers_master.csv
outputs/semantic_similarity_relations_embeddings.csv
outputs/paper_topics.csv
outputs/topics_info.csv
outputs/paper_galaxies.csv
outputs/funding_entities.csv
outputs/organization_ror_matches.csv
outputs/kg.ttl
outputs/provenance.json
outputs/provenance.ttl
ro-crate-metadata.json
```

---

## 9. Resultado de validación

La validación final se ejecuta con:

```bash
python src/validate_kg.py
```

Ejemplo de salida esperada:

```text
KG: OK
Provenance: OK
Validacion completada correctamente.
```

El KG final contiene papers, autores, topics, similitud semántica, entidades NER/funding y organizaciones enriquecidas con ROR cuando existe correspondencia fiable.

---

## 10. Notas sobre NER/funding

Los modelos NER generales no detectan directamente clases específicas como `FUNDER`, `GRANT_ID` o `PROJECT_ID`.

Por ello, la extracción final combina:

```text
dslim/bert-base-NER
regex para grants y project IDs
reglas de contexto para funders
postprocesado para eliminar falsos positivos
```

Esta decisión se justifica mediante la comparación de modelos HuggingFace sobre un gold standard manual.

---

## 11. Notas sobre ROR

El enriquecimiento ROR es automático y conservador. Solo se integran en el KG los matches marcados como `chosen:true` por la API de ROR.

No todas las organizaciones extraídas por NER pueden normalizarse con ROR, ya que algunas son acrónimos ambiguos, consorcios, instrumentos, programas científicos o menciones parciales.

---

## 12. Comando completo de regeneración rápida

Una vez descargados los PDFs y generado el CSV maestro, se puede regenerar la parte analítica y el KG con:

```bash
python src/generate_similarity.py --allow-download

python src/generate_topics.py --allow-download

python evaluation/ner/evaluate_hf_ner_models.py --allow-download

python src/funding.py --allow-download

python src/enrich_organizations_ror.py

python src/build_kg.py \
  --similarity outputs/semantic_similarity_relations_embeddings.csv \
  --topics outputs/paper_topics.csv \
  --funding outputs/funding_entities.csv \
  --ror outputs/organization_ror_matches.csv

python src/generate_provenance.py

python src/generate_rocrate.py

python src/validate_kg.py
```

---

## 13. Licencia

Este repositorio se desarrolla como parte de la práctica de la asignatura Open Science and Artificial Intelligence in Research Software Engineering.
