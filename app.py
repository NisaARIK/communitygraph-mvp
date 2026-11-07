
import streamlit as st
import pandas as pd
from neo4j import GraphDatabase

st.set_page_config(
    page_title="CommunityGraph",
    page_icon="🌐",
    layout="wide"
)

@st.cache_resource
def get_driver():
    return GraphDatabase.driver(
        st.secrets["NEO4J_URI"],
        auth=(
            st.secrets["NEO4J_USERNAME"],
            st.secrets["NEO4J_PASSWORD"]
        )
    )

def get_database():
    return st.secrets["NEO4J_DATABASE"]

def run_query(query, **params):
    records, _, _ = get_driver().execute_query(
        query,
        database_=get_database(),
        **params
    )
    return [dict(r) for r in records]

st.title("🌐 CommunityGraph")
st.caption(
    "Find the right people to solve the right problems."
)

st.divider()

try:
    problems = run_query("""
        MATCH (p:Problem)
        RETURN p.id AS id, p.name AS name
        ORDER BY name
    """)

    if not problems:
        st.warning("No startup problems found.")
        st.stop()

    problem_options = {
        p["name"]: p["id"]
        for p in problems
    }

    selected_name = st.selectbox(
        "Select a startup problem",
        list(problem_options.keys())
    )

    selected_id = problem_options[selected_name]

    st.subheader("Recommended Experts")

    matches = run_query("""
        MATCH (u:User)-[r:MATCHED_WITH]->
              (p:Problem {id: $problem_id})
        RETURN
            u.name AS expert,
            u.role AS role,
            r.score AS score,
            r.explanation AS explanation
        ORDER BY score DESC
    """, problem_id=selected_id)

    if not matches:
        st.info(
            "No saved recommendations for this problem yet."
        )

    for match in matches:
        score = float(match["score"])

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {match['expert']}")
                st.write(match["role"])

            with col2:
                st.metric(
                    "Match Score",
                    f"{score * 100:.1f}%"
                )

            st.progress(max(0.0, min(1.0, score)))

            with st.expander("Why this match?"):
                st.write(
                    match["explanation"]
                    or "No explanation available."
                )

    st.divider()

    st.subheader("Graph Statistics")

    stats = run_query("""
        MATCH (n)
        RETURN
            count(n) AS total_nodes
    """)

    rel_stats = run_query("""
        MATCH ()-[r]->()
        RETURN count(r) AS total_edges
    """)

    c1, c2, c3 = st.columns(3)

    c1.metric("Graph Nodes", stats[0]["total_nodes"])
    c2.metric("Graph Edges", rel_stats[0]["total_edges"])
    c3.metric("Recommended Experts", len(matches))

except Exception:
    st.error(
        "Could not load graph data. "
        "Check the database connection and configuration."
    )
    st.stop()
