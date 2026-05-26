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
    results = graph.query(query)
    rows = []

    for row in results:
        rows.append({str(var): str(value) for var, value in row.asdict().items()})

    return pd.DataFrame(rows)


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

    SELECT ?topicLabel ?topicScore
    WHERE {{
      <{paper_uri}> onto:hasTopicAssignment ?assignment .
      ?assignment onto:assignedTopic ?topic ;
                  onto:topicScore ?topicScore .
      ?topic onto:topicLabel ?topicLabel .
    }}
    ORDER BY DESC(?topicScore)
    """

    return query_df(graph, query)


def get_similar_papers(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?similarPaper ?similarTitle ?score ?metric
    WHERE {{
      <{paper_uri}> onto:hasSimilarityRelation ?relation .
      ?relation onto:similarPaper ?similarPaper ;
                onto:similarityScore ?score ;
                onto:similarityMetric ?metric .
      ?similarPaper onto:title ?similarTitle .
    }}
    ORDER BY DESC(?score)
    """

    return query_df(graph, query)


def get_acknowledged_organizations(graph, paper_uri):
    query = f"""
    PREFIX onto: <{ONTO}>

    SELECT ?organizationName ?entityType ?confidence
    WHERE {{
      <{paper_uri}> onto:acknowledgesOrganization ?organization .
      ?organization onto:organizationName ?organizationName .
      OPTIONAL {{ ?organization onto:entityType ?entityType . }}
      OPTIONAL {{ ?organization onto:confidenceScore ?confidence . }}
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

    SELECT ?projectName ?fundingID ?entityType ?confidence
    WHERE {{
      <{paper_uri}> onto:fundedBy ?project .
      ?project a onto:Project ;
               onto:projectName ?projectName ;
               onto:fundingID ?fundingID .
      OPTIONAL {{ ?project onto:entityType ?entityType . }}
      OPTIONAL {{ ?project onto:confidenceScore ?confidence . }}
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
    if df.empty:
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
    st.caption("Demo para consumir el Knowledge Graph generado a partir de 30 papers de Astrophysics of Galaxies.")

    graph = load_graph()

    st.sidebar.header("Navegación")
    page = st.sidebar.radio(
        "Selecciona una vista",
        [
            "Resumen del KG",
            "Explorador de papers",
            "Organizaciones",
            "Provenance",
        ],
    )

    if page == "Resumen del KG":
        st.header("Resumen del Knowledge Graph")

        col1, col2 = st.columns([1, 2])

        counts = get_counts(graph)

        with col1:
            st.subheader("Conteos")
            show_df(counts, "No se encontraron conteos.")

        with col2:
            st.subheader("Qué demuestra esta demo")
            st.markdown(
                """
                Esta aplicación consume directamente los ficheros RDF:

                - `outputs/kg.ttl`
                - `outputs/provenance.ttl`

                La demo permite explorar papers, autores, topics, similitud semántica,
                entidades NER extraídas de acknowledgements, grants y provenance del pipeline.
                """
            )

        st.subheader("Top organizaciones reconocidas")
        show_df(get_top_organizations(graph), "No se encontraron organizaciones.")

    elif page == "Explorador de papers":
        st.header("Explorador de artículos")

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
                with st.expander("Abstract"):
                    st.write(abstract)

        tab_authors, tab_topics, tab_similarity, tab_orgs, tab_people, tab_funding = st.tabs(
            [
                "Autores",
                "Topic",
                "Papers similares",
                "Organizaciones",
                "Personas agradecidas",
                "Funding / Grants",
            ]
        )

        with tab_authors:
            st.subheader("Autores")
            show_df(get_authors(graph, selected_paper), "Este paper no tiene autores registrados.")

        with tab_topics:
            st.subheader("Topic asignado")
            show_df(get_topics(graph, selected_paper), "Este paper no tiene topic asignado.")

        with tab_similarity:
            st.subheader("Papers similares")
            show_df(get_similar_papers(graph, selected_paper), "No hay relaciones de similitud para este paper.")

        with tab_orgs:
            st.subheader("Organizaciones reconocidas en acknowledgements")
            show_df(
                get_acknowledged_organizations(graph, selected_paper),
                "No hay organizaciones reconocidas para este paper.",
            )

        with tab_people:
            st.subheader("Personas reconocidas en acknowledgements")
            show_df(
                get_acknowledged_people(graph, selected_paper),
                "No hay personas reconocidas para este paper.",
            )

        with tab_funding:
            st.subheader("Funding IDs / Grants")
            show_df(
                get_funding(graph, selected_paper),
                "No hay grants o funding IDs registrados para este paper.",
            )

    elif page == "Organizaciones":
        st.header("Organizaciones reconocidas")

        st.markdown(
            """
            Esta vista muestra las organizaciones detectadas en la sección de acknowledgements
            y cuántas veces aparecen enlazadas desde papers.
            """
        )

        show_df(get_top_organizations(graph), "No se encontraron organizaciones.")

    elif page == "Provenance":
        st.header("Provenance del pipeline")

        st.markdown(
            """
            Esta vista consume `outputs/provenance.ttl` y muestra las actividades registradas
            con PROV-O: scripts, modelos, inputs y outputs del workflow.
            """
        )

        show_df(
            get_provenance_activities(graph),
            "No se encontraron actividades de provenance.",
        )


if __name__ == "__main__":
    main()