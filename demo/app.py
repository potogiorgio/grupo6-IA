from pathlib import Path

import pandas as pd
import streamlit as st
from rdflib import Graph


KG_PATH = Path("outputs/kg.ttl")
PROVENANCE_PATH = Path("outputs/provenance.ttl")

ONTO = "https://w3id.org/grupo6-ia/ontology#"
PROV = "http://www.w3.org/ns/prov#"
DCTERMS = "http://purl.org/dc/terms/"


@st.cache_resource
def load_graph():
    graph = Graph()

    if not KG_PATH.exists():
        st.error(f"No se encuentra {KG_PATH}")
        st.stop()

    graph.parse(KG_PATH, format="turtle")

    if PROVENANCE_PATH.exists():
        graph.parse(PROVENANCE_PATH, format="turtle")

    return graph


def query_df(graph, query):
    try:
        results = graph.query(query)
        rows = []

        for row in results:
            rows.append({str(var): str(value) for var, value in row.asdict().items()})

        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error al ejecutar la consulta: {e}")
        return pd.DataFrame()


def get_papers(graph):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?paper ?title
    WHERE {{
      ?paper a onto:Paper ;
             onto:title ?title .
    }}
    ORDER BY ?title
    """

    return query_df(graph, query)


def get_paper_details(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?title ?abstract
    WHERE {{
      <{paper_uri}> a onto:Paper ;
                    onto:title ?title .
      OPTIONAL {{ <{paper_uri}> onto:abstract ?abstract . }}
    }}
    """

    return query_df(graph, query)


def get_authors(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?authorName
    WHERE {{
      <{paper_uri}> onto:hasAuthor ?author .
      ?author onto:personName ?authorName .
    }}
    ORDER BY ?authorName
    """

    return query_df(graph, query)


def get_topics(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?topicLabel ?topicScore ?threshold
    WHERE {{
      <{paper_uri}> onto:hasTopicAssignment ?assignment .
      ?assignment onto:assignedTopic ?topic ;
                  onto:topicScore ?topicScore .
      ?topic onto:topicLabel ?topicLabel .
      OPTIONAL {{ ?assignment onto:threshold ?threshold . }}
    }}
    ORDER BY DESC(?topicScore)
    """

    return query_df(graph, query)


def get_similar_papers(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?similarTitle ?score ?threshold ?metric
    WHERE {{
      <{paper_uri}> onto:hasSimilarityRelation ?relation .
      ?relation onto:similarPaper ?similarPaper ;
                onto:similarityScore ?score ;
                onto:similarityMetric ?metric .
      ?similarPaper onto:title ?similarTitle .
      OPTIONAL {{ ?relation onto:threshold ?threshold . }}
    }}
    ORDER BY DESC(?score)
    """

    return query_df(graph, query)


def get_galaxies(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?galaxyName ?mentionText ?section ?wikidataID
    WHERE {{
      <{paper_uri}> onto:hasGalaxyStudyEvidence ?evidence .
      ?evidence onto:identifiesGalaxy ?galaxy ;
                onto:mentionText ?mentionText ;
                onto:sourceSection ?section .
      ?galaxy onto:galaxyName ?galaxyName .
      OPTIONAL {{ ?galaxy onto:galaxyWikidataID ?wikidataID . }}
    }}
    ORDER BY ?galaxyName
    """
    
    return query_df(graph, query)


def get_acknowledged_organizations(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?organizationName ?entityType ?rorID ?wikidataID ?country
    WHERE {{
      <{paper_uri}> onto:acknowledgesOrganization ?organization .
      ?organization onto:organizationName ?organizationName .
      OPTIONAL {{ ?organization onto:entityType ?entityType . }}
      OPTIONAL {{ ?organization onto:rorID ?rorID . }}
      OPTIONAL {{ ?organization onto:organizationWikidataID ?wikidataID . }}
      OPTIONAL {{ ?organization onto:country ?country . }}
    }}
    ORDER BY ?organizationName
    """

    return query_df(graph, query)


def get_acknowledged_people(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?personName ?confidence
    WHERE {{
      <{paper_uri}> onto:acknowledgesPerson ?person .
      ?person onto:personName ?personName .
      OPTIONAL {{ ?person onto:confidenceScore ?confidence . }}
    }}
    ORDER BY ?personName
    """

    return query_df(graph, query)


def get_funding(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?projectName ?fundingID ?entityType
    WHERE {{
      <{paper_uri}> onto:fundedBy ?project .
      ?project a onto:Project ;
               onto:projectName ?projectName ;
               onto:fundingID ?fundingID .
      OPTIONAL {{ ?project onto:entityType ?entityType . }}
    }}
    ORDER BY ?fundingID
    """

    return query_df(graph, query)


def get_counts(graph):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?type (COUNT(?resource) AS ?count)
    WHERE {{
      VALUES ?type {{
        onto:Paper
        onto:Person
        onto:Organization
        onto:Project
        onto:Topic
        onto:TopicAssignment
        onto:SimilarityRelation
        onto:Galaxy
        onto:GalaxyStudyEvidence
      }}

      ?resource a ?type .
    }}
    GROUP BY ?type
    ORDER BY DESC(?count)
    """

    df = query_df(graph, query)

    if df.empty:
        return df

    df["type"] = df["type"].str.replace(ONTO, "", regex=False)
    return df


def get_top_organizations(graph):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?organizationName (COUNT(?paper) AS ?mentions)
    WHERE {{
      ?paper a onto:Paper ;
             onto:acknowledgesOrganization ?organization .
      ?organization onto:organizationName ?organizationName .
    }}
    GROUP BY ?organizationName
    ORDER BY DESC(?mentions)
    LIMIT 20
    """

    return query_df(graph, query)


def get_top_galaxies(graph):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?galaxyName (COUNT(?paper) AS ?mentions)
    WHERE {{
      ?paper a onto:Paper ;
             onto:studiesGalaxy ?galaxy .
      ?galaxy onto:galaxyName ?galaxyName .
    }}
    GROUP BY ?galaxyName
    ORDER BY DESC(?mentions)
    LIMIT 20
    """

    return query_df(graph, query)


def get_provenance_activities(graph):
    query = f"""
    PREFIX prov: <{PROV}>
    PREFIX dcterms: <{DCTERMS}>

    SELECT ?title ?description
    WHERE {{
      ?activity a prov:Activity ;
                dcterms:title ?title ;
                dcterms:description ?description .
    }}
    ORDER BY ?title
    """

    return query_df(graph, query)


def show_df(df, empty_message):
    if df is None or df.empty:
        st.info(empty_message)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(
        page_title="Grupo 6 IA - KG Explorer",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 Knowledge Graph Explorer")
    st.caption("Demo interactiva para explorar el Grafo de Conocimiento y realizar consultas SPARQL (Astrophysics of Galaxies).")

    graph = load_graph()

    st.sidebar.header("Navegación")
    page = st.sidebar.radio(
        "Selecciona una vista",
        [
            "Resumen del KG",
            "Explorador de papers",
            "Consulta SPARQL Libre",
            "Organizaciones y Galaxias",
            "Provenance",
        ],
    )

    if page == "Resumen del KG":
        st.header("Resumen del Knowledge Graph")

        col1, col2 = st.columns([1, 2])

        counts = get_counts(graph)

        with col1:
            st.subheader("Entidades en el Grafo")
            show_df(counts, "No se encontraron conteos.")

        with col2:
            st.subheader("Acerca de esta aplicación")
            st.markdown(
                """
                Esta aplicación carga en memoria y consulta de forma dinámica los archivos Turtle generados por la pipeline:

                - `outputs/kg.ttl` (Grafo principal)
                - `outputs/provenance.ttl` (Trazabilidad PROV-O)

                **Novedades implementadas:**
                - Extracción y visualización de **Galaxias** (ej. Andromeda, Milky Way).
                - Inclusión de **umbrales (thresholds)** en Topics y Similitudes semánticas.
                - Herramienta de **consulta SPARQL libre** integrada en el menú.
                """
            )

    elif page == "Explorador de papers":
        st.header("Explorador de artículos científicos")

        papers = get_papers(graph)

        if papers.empty:
            st.error("No se han encontrado papers en el KG.")
            st.stop()

        paper_options = {
            row["title"]: row["paper"]
            for _, row in papers.iterrows()
        }

        selected_title = st.selectbox("Selecciona un paper", list(paper_options.keys()))
        selected_paper = paper_options[selected_title]

        details = get_paper_details(graph, selected_paper)

        if not details.empty:
            st.subheader(details.iloc[0]["title"])

            abstract = details.iloc[0].get("abstract", "")
            if abstract:
                with st.expander("Abstract del Paper", expanded=False):
                    st.write(abstract)

        tabs = st.tabs(
            [
                "🔭 Galaxias Estudiadas",
                "🧠 Topics (IA)",
                "🔗 Similitud Semántica",
                "👥 Autores",
                "🏢 Organizaciones / Funding",
            ]
        )

        with tabs[0]:
            st.subheader("Objetos Astronómicos")
            show_df(get_galaxies(graph, selected_paper), "No se han detectado galaxias en el título/abstract de este paper.")

        with tabs[1]:
            st.subheader("Topics asignados (BERTopic)")
            show_df(get_topics(graph, selected_paper), "Este paper no tiene topic asignado.")

        with tabs[2]:
            st.subheader("Papers más similares (HuggingFace Embeddings)")
            show_df(get_similar_papers(graph, selected_paper), "No hay relaciones de similitud para este paper.")

        with tabs[3]:
            st.subheader("Autores")
            show_df(get_authors(graph, selected_paper), "Este paper no tiene autores registrados.")

        with tabs[4]:
            colA, colB = st.columns(2)
            with colA:
                st.subheader("Organizaciones (Agradecimientos)")
                show_df(
                    get_acknowledged_organizations(graph, selected_paper),
                    "No hay organizaciones reconocidas.",
                )
                st.subheader("Personas (Agradecimientos)")
                show_df(
                    get_acknowledged_people(graph, selected_paper),
                    "No hay personas reconocidas.",
                )
            with colB:
                st.subheader("Funding IDs / Proyectos")
                show_df(
                    get_funding(graph, selected_paper),
                    "No hay grants o funding IDs registrados.",
                )

    elif page == "Consulta SPARQL Libre":
        st.header("Consola de Consultas SPARQL")
        
        st.markdown("Escribe y ejecuta consultas directamente sobre la ontología. Los namespaces `onto:` y `kg:` ya están precargados en el motor subyacente o puedes redefinirlos.")

        default_query = f"""PREFIX onto: <{ONTO}>
PREFIX kg: <https://w3id.org/grupo6-ia/resource/>

SELECT ?paperTitle ?galaxyName
WHERE {{
  ?paper a onto:Paper ;
         onto:title ?paperTitle ;
         onto:studiesGalaxy ?galaxy .
  ?galaxy onto:galaxyName ?galaxyName .
}}
LIMIT 15
"""

        query = st.text_area("Consulta SPARQL", value=default_query, height=250)
        
        if st.button("Ejecutar Consulta", type="primary"):
            with st.spinner("Ejecutando SPARQL..."):
                df_results = query_df(graph, query)
                st.success(f"Consulta completada. Filas devueltas: {len(df_results) if df_results is not None else 0}")
                show_df(df_results, "La consulta no devolvió resultados.")

    elif page == "Organizaciones y Galaxias":
        st.header("Estadísticas Generales")

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 20 Galaxias Estudiadas")
            show_df(get_top_galaxies(graph), "No se encontraron galaxias.")
            
        with col2:
            st.subheader("Top 20 Organizaciones (Acknowledgements)")
            show_df(get_top_organizations(graph), "No se encontraron organizaciones.")

    elif page == "Provenance":
        st.header("Trazabilidad y Provenance (PROV-O)")

        st.markdown(
            """
            Esta vista muestra las actividades registradas en el pipeline de IA y extracción:
            scripts ejecutados, modelos empleados, inputs procesados y outputs generados.
            """
        )

        show_df(
            get_provenance_activities(graph),
            "No se encontraron actividades de provenance.",
        )


if __name__ == "__main__":
    main()
