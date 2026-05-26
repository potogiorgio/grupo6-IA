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

### 6.1. Iniciar GROBID

```bash
docker compose up -d grobid
```

Comprobar que GROBID está activo:

```bash
curl http://localhost:8070/api/isalive
```

En PowerShell:

```powershell
Invoke-WebRequest -Uri http://localhost:8070/api/isalive
```

---

### 6.2. Descargar PDFs

```bash
python src/download_pdfs.py
```

Este paso descarga los PDFs de los papers seleccionados.

---

### 6.3. Procesar PDFs con GROBID

```bash
python src/run_grobid.py --limit 0
```

Este paso genera ficheros TEI XML a partir de los PDFs.

---

### 6.4. Generar CSV maestro

```bash
python src/extract_papers_master.py
```

Este paso genera:

```text
data/intermediate/papers_master.csv
```

El fichero maestro contiene metadatos, títulos, abstracts, autores y acknowledgements.

---

### 6.5. Generar similitud semántica entre papers

Primera ejecución, permitiendo descarga de modelos:

```bash
python src/generate_similarity.py --allow-download
```

Si los modelos ya están descargados:

```bash
python src/generate_similarity.py
```

Este paso genera:

```text
outputs/semantic_similarity_relations_embeddings.csv
```

El modelo utilizado es:

```text
sentence-transformers/all-mpnet-base-v2
```

---

### 6.6. Generar topics

Primera ejecución, permitiendo descarga de modelos:

```bash
python src/generate_topics.py --allow-download
```

Si los modelos ya están descargados:

```bash
python src/generate_topics.py
```

Este paso genera:

```text
outputs/paper_topics.csv
outputs/topics_info.csv
```

La generación de topics utiliza embeddings, BERTopic, UMAP y HDBSCAN.

---

### 6.7. Evaluar modelos NER

```bash
python evaluation/ner/evaluate_hf_ner_models.py --allow-download
```

Este paso compara varios modelos HuggingFace sobre un gold standard manual:

```text
data/evaluation/ner/ner_gold.csv
```

y genera:

```text
data/evaluation/ner/ner_model_comparison.csv
```

El modelo seleccionado para la extracción final es:

```text
dslim/bert-base-NER
```

La extracción final combina:

- HuggingFace NER para `PERSON` y `ORGANIZATION`;
- expresiones regulares para `GRANT_ID` y `PROJECT_ID`;
- reglas de contexto para `FUNDER`.

---

### 6.8. Extraer entidades NER/funding

```bash
python src/funding.py --allow-download
```

Si el modelo ya está descargado:

```bash
python src/funding.py
```

Este paso genera:

```text
outputs/funding_entities.csv
```

El fichero contiene entidades extraídas de acknowledgements:

```text
PERSON
ORGANIZATION
FUNDER
GRANT_ID
PROJECT_ID
```

---

### 6.9. Enriquecer organizaciones con ROR

Primero se puede probar con un límite pequeño:

```bash
python src/enrich_organizations_ror.py --limit 20
```

Ejecución completa:

```bash
python src/enrich_organizations_ror.py
```

Este paso genera:

```text
outputs/organization_ror_matches.csv
```

El enriquecimiento con ROR permite añadir identificadores persistentes y país a algunas organizaciones detectadas.

Solo se integran en el KG los resultados marcados como:

```text
matched = yes
chosen = yes
```

---

### 6.10. Construir el Knowledge Graph

```bash
python src/build_kg.py \
  --similarity outputs/semantic_similarity_relations_embeddings.csv \
  --topics outputs/paper_topics.csv \
  --funding outputs/funding_entities.csv \
  --ror outputs/organization_ror_matches.csv
```

Este paso genera:

```text
outputs/kg.ttl
```

El KG integra:

- papers;
- autores;
- topics;
- relaciones de similitud;
- personas reconocidas en acknowledgements;
- organizaciones reconocidas en acknowledgements;
- grants y funding IDs;
- identificadores ROR cuando están disponibles.

---

### 6.11. Generar provenance

```bash
python src/generate_provenance.py
```

Este paso genera:

```text
outputs/provenance.json
outputs/provenance.ttl
```

La provenance registra:

- scripts ejecutados;
- inputs;
- outputs;
- modelos usados;
- actividades de la pipeline.

---

### 6.12. Generar RO-Crate

```bash
python src/generate_rocrate.py
```

Este paso genera:

```text
ro-crate-metadata.json
```

El RO-Crate describe el proyecto como Research Object e incluye datos, código, outputs, KG, provenance, queries, modelos y workflow.

---

### 6.13. Validar KG y provenance

```bash
python src/validate_kg.py
```

La validación comprueba que:

- `outputs/kg.ttl` parsea correctamente como Turtle;
- `outputs/provenance.ttl` parsea correctamente como Turtle;
- existen papers, autores, topics, relaciones de similitud y entidades de funding;
- existen relaciones `acknowledgesOrganization`, `acknowledgesPerson`, `fundedBy` y `fundingID`;
- las referencias a autores, organizaciones, proyectos, topics y relaciones de similitud están definidas;
- no aparecen falsos positivos conocidos como `project_that`, `project_with` o `project_and`.

También puede validarse solo el KG:

```bash
python src/validate_kg.py --skip-provenance
```

---
## 7. Demo Streamlit

La demo permite consumir el Knowledge Graph mediante una interfaz visual.

Ejecutar:

```bash
streamlit run demo/app.py
```

La demo carga:

```text
outputs/kg.ttl
outputs/provenance.ttl
```

y permite explorar:

- resumen del KG;
- queries SPARQL;
- explorador de papers;
- autores;
- topics;
- papers similares;
- organizaciones reconocidas;
- personas reconocidas;
- funding IDs;
- organizaciones enriquecidas con ROR;
- provenance del pipeline;
- visualizaciones de topics y organizaciones.

---

## 8. Outputs principales

Los principales resultados generados por la pipeline son:

```text
data/intermediate/papers_master.csv
outputs/semantic_similarity_relations_embeddings.csv
outputs/paper_topics.csv
outputs/topics_info.csv
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
