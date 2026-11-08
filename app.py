
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

# COMMUNITYGRAPH v0.2
# Create Startup Problem

import uuid
import hmac

st.divider()
st.header("Create Startup Problem")

admin_password = st.text_input(
    "Admin password",
    type="password",
    key="admin_password"
)

expected_password = st.secrets.get("ADMIN_PASSWORD", "")

is_admin = bool(
    expected_password
    and hmac.compare_digest(
        admin_password,
        expected_password
    )
)

if not is_admin:
    st.info(
        "Enter the admin password to create a problem."
    )
else:
    founders = run_query("""
        MATCH (u:User)
        WHERE u.role = 'Founder'
        RETURN u.id AS id, u.name AS name
        ORDER BY name
    """)

    if not founders:
        st.warning("No founders found.")
    else:
        founder_options = {
            f["name"]: f["id"]
            for f in founders
        }

        with st.form("create_problem_form"):

            title = st.text_input(
                "Problem title"
            )

            description = st.text_area(
                "Problem description"
            )

            sector = st.text_input(
                "Industry",
                placeholder="HealthTech"
            )

            skills_text = st.text_input(
                "Required skills",
                placeholder="Python, Machine Learning"
            )

            founder_name = st.selectbox(
                "Problem owner",
                list(founder_options.keys())
            )

            submitted = st.form_submit_button(
                "Create Problem"
            )

        if submitted:

            skills = list(dict.fromkeys(
                s.strip()
                for s in skills_text.split(",")
                if s.strip()
            ))

            if not title.strip() or not sector.strip() or not skills:
                st.error(
                    "Title, industry and skills are required."
                )
            else:
                problem_id = "p_" + uuid.uuid4().hex[:12]

                try:
                    run_query("""
                        MATCH (owner:User {id: $owner_id})

                        CREATE (p:Problem {
                            id: $problem_id,
                            name: $title,
                            description: $description,
                            sector: $sector
                        })

                        CREATE (owner)-[:OWNS]->(p)

                        MERGE (industry:Sector {
                            id: $sector_id
                        })
                        ON CREATE SET
                            industry.name = $sector,
                            industry.type = 'Sector'

                        CREATE (p)-[:IN_SECTOR]->(industry)

                        WITH p
                        UNWIND $skills AS skill_name

                        MERGE (s:Skill {
                            id: 'skill:' + skill_name
                        })
                        ON CREATE SET
                            s.name = skill_name,
                            s.type = 'Skill'

                        CREATE (p)-[:REQUIRES]->(s)

                        RETURN p.id AS id
                    """,
                        owner_id=founder_options[founder_name],
                        problem_id=problem_id,
                        title=title.strip(),
                        description=description.strip(),
                        sector=sector.strip(),
                        sector_id="sector:" + sector.strip(),
                        skills=skills
                    )

                    st.success(
                        "Startup problem created successfully!"
                    )

                    st.info(
                        "Problem saved to Neo4j. "
                        "Expert matching will be added next."
                    )

                except Exception:
                    st.error(
                        "Could not save the problem. "
                        "Check the application logs."
                    )

# COMMUNITYGRAPH v0.2
# Automatic Expert Matching

def calculate_expert_matches(problem_id):

    problem_rows = run_query("""
        MATCH (p:Problem {id: $problem_id})

        OPTIONAL MATCH (p)-[:REQUIRES]->(s:Skill)

        WITH p, collect(DISTINCT s.name) AS skills

        OPTIONAL MATCH (p)-[:IN_SECTOR]->(sector:Sector)

        OPTIONAL MATCH (owner:User)-[:OWNS]->(p)

        RETURN
            p.id AS id,
            skills AS required_skills,
            sector.name AS sector,
            owner.id AS owner_id
    """, problem_id=problem_id)

    if not problem_rows:
        return []

    problem = problem_rows[0]

    required_skills = set(
        s for s in problem["required_skills"] if s
    )

    experts = run_query("""
        MATCH (u:User)

        WHERE u.id <> $owner_id
          AND u.role <> 'Founder'

        OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)

        WITH u, collect(DISTINCT s.name) AS skills

        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(sector:Sector)

        RETURN
            u.id AS id,
            u.name AS name,
            u.role AS role,
            skills AS skills,
            collect(DISTINCT sector.name) AS interests
    """, owner_id=problem["owner_id"])

    # Common skill/sector features with the founder
    feature_rows = run_query("""
        MATCH (owner:User {id: $owner_id})

        MATCH (expert:User)
        WHERE expert.id <> $owner_id

        OPTIONAL MATCH (owner)-[:HAS_SKILL|INTERESTED_IN]->(of)
        WITH owner, expert,
             collect(DISTINCT of.id) AS owner_features

        OPTIONAL MATCH (expert)-[:HAS_SKILL|INTERESTED_IN]->(ef)

        RETURN expert.id AS id,
               owner_features AS owner_features,
               collect(DISTINCT ef.id) AS expert_features
    """, owner_id=problem["owner_id"])

    feature_map = {
        r["id"]: r for r in feature_rows
    }

    results = []

    for expert in experts:

        expert_skills = set(
            s for s in expert["skills"] if s
        )

        matched_skills = (
            required_skills & expert_skills
        )

        skill_score = (
            len(matched_skills) / len(required_skills)
            if required_skills else 0.0
        )

        industry_score = float(
            problem["sector"] in expert["interests"]
        )

        features = feature_map.get(expert["id"], {})

        founder_features = set(
            x for x in features.get(
                "owner_features", []
            ) if x
        )

        expert_features = set(
            x for x in features.get(
                "expert_features", []
            ) if x
        )

        union = founder_features | expert_features

        graph_score = (
            len(founder_features & expert_features)
            / len(union)
            if union else 0.0
        )

        score = (
            0.65 * skill_score
            + 0.25 * industry_score
            + 0.10 * graph_score
        )

        missing_skills = sorted(
            required_skills - expert_skills
        )

        if score < 0.40:
            continue

        explanation = []

        if matched_skills:
            explanation.append(
                "Matching skills: "
                + ", ".join(sorted(matched_skills))
            )

        if industry_score:
            explanation.append(
                "Interested in the target industry"
            )

        if graph_score:
            explanation.append(
                "Shares skills or sector interests "
                "with the founder"
            )

        results.append({
            "expert_id": expert["id"],
            "expert": expert["name"],
            "role": expert["role"],
            "score": round(score, 4),
            "matched_skills": sorted(matched_skills),
            "missing_skills": missing_skills,
            "explanation": " | ".join(explanation)
        })

    return sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

# Find Experts interface

st.divider()
st.header("Find Experts")

try:
    available_problems = run_query("""
        MATCH (p:Problem)
        RETURN p.id AS id, p.name AS name
        ORDER BY name
    """)

    problem_options = {
        f"{p['name']} ({p['id']})": p["id"]
        for p in available_problems
    }

    if not problem_options:
        st.info("No problems available.")
    else:
        selected_problem = st.selectbox(
            "Choose a problem",
            list(problem_options.keys()),
            key="matching_problem"
        )

        if st.button(
            "Find Experts",
            type="primary"
        ):
            selected_id = problem_options[selected_problem]

            matches = calculate_expert_matches(
                selected_id
            )

            if not matches:
                st.warning(
                    "No experts meet the current "
                    "matching threshold."
                )
            else:
                st.success(
                    f"{len(matches)} experts found!"
                )

                for match in matches:

                    with st.container(border=True):

                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.subheader(match["expert"])
                            st.write(match["role"])

                        with col2:
                            st.metric(
                                "Match Score",
                                f"{match['score'] * 100:.1f}%"
                            )

                        st.progress(match["score"])

                        st.write(
                            "Matched skills:",
                            ", ".join(match["matched_skills"])
                            or "None"
                        )

                        st.write(
                            "Missing skills:",
                            ", ".join(match["missing_skills"])
                            or "None"
                        )

                        with st.expander("Why this match?"):
                            st.write(match["explanation"])

except Exception:
    st.error(
        "Could not calculate expert matches. "
        "Check application logs."
    )

# CommunityGraph v0.3
# Persist expert recommendations to Neo4j

def save_expert_matches(problem_id, matches):

    saved_count = 0

    for match in matches:

        rows = run_query("""
            MATCH (p:Problem {id: $problem_id})
            MATCH (u:User {id: $expert_id})

            MERGE (p)-[r:MATCHED_WITH]->(u)

            SET r.score = $score,
                r.explanation = $explanation,
                r.updated_at = datetime()

            RETURN p.id AS problem_id
        """,
            problem_id=problem_id,
            expert_id=match["expert_id"],
            score=float(match["score"]),
            explanation=match["explanation"]
        )

        if rows:
            saved_count += 1

    return saved_count

# Admin-only match persistence

st.divider()
st.subheader("Save Expert Matches")

save_password = st.text_input(
    "Admin password to save matches",
    type="password",
    key="save_matches_password"
)

expected_admin = st.secrets.get(
    "ADMIN_PASSWORD", ""
)

can_save = bool(
    expected_admin
    and hmac.compare_digest(
        save_password,
        expected_admin
    )
)

if not can_save:
    st.info("Admin access is required to save matches.")

else:
    problems_to_save = run_query("""
        MATCH (p:Problem)
        RETURN p.id AS id, p.name AS name
        ORDER BY name
    """)

    if problems_to_save:

        options = {
            f"{p['name']} ({p['id']})": p["id"]
            for p in problems_to_save
        }

        selected = st.selectbox(
            "Problem",
            list(options.keys()),
            key="save_match_problem"
        )

        if st.button("Calculate and Save Matches"):

            problem_id = options[selected]

            try:
                matches = calculate_expert_matches(
                    problem_id
                )

                if matches:
                    count = save_expert_matches(
                        problem_id,
                        matches
                    )

                    st.success(
                        f"{count} matches saved to Neo4j!"
                    )

                else:
                    st.warning(
                        "No matches meet the threshold."
                    )

            except Exception:
                st.error(
                    "Could not save matches. "
                    "Check application logs."
                )

# COMMUNITYGRAPH v0.4
# User and Expert Profile Creation

def create_user_profile(name, role, skills, interests):

    import uuid

    user_id = "u_" + uuid.uuid4().hex[:12]

    rows = run_query("""
        CREATE (u:User {
            id: $user_id,
            name: $name,
            role: $role
        })

        WITH u

        FOREACH (skill_name IN $skills |
            MERGE (s:Skill {
                id: 'skill:' + skill_name
            })
            ON CREATE SET
                s.name = skill_name,
                s.type = 'Skill'

            MERGE (u)-[:HAS_SKILL]->(s)
        )

        WITH u

        FOREACH (sector_name IN $interests |
            MERGE (sector:Sector {
                id: 'sector:' + sector_name
            })
            ON CREATE SET
                sector.name = sector_name,
                sector.type = 'Sector'

            MERGE (u)-[:INTERESTED_IN]->(sector)
        )

        RETURN u.id AS id
    """,
        user_id=user_id,
        name=name,
        role=role,
        skills=skills,
        interests=interests
    )

    return rows[0]["id"] if rows else None

# Profile creation interface

st.divider()
st.header("Create Expert Profile")

profile_password = st.text_input(
    "Admin password for profile creation",
    type="password",
    key="profile_admin_password"
)

expected_admin = st.secrets.get(
    "ADMIN_PASSWORD", ""
)

can_create_profile = bool(
    expected_admin
    and hmac.compare_digest(
        profile_password,
        expected_admin
    )
)

if not can_create_profile:
    st.info(
        "Admin access is required to create profiles."
    )

else:
    with st.form("create_profile_form"):

        name = st.text_input(
            "Full name"
        )

        role = st.selectbox(
            "Professional role",
            [
                "ML Engineer",
                "Data Scientist",
                "Developer",
                "Designer",
                "Founder",
                "Researcher",
                "Product Manager"
            ]
        )

        skills_text = st.text_input(
            "Skills (comma-separated)",
            placeholder="Python, Machine Learning, NLP"
        )

        interests_text = st.text_input(
            "Industry interests (comma-separated)",
            placeholder="AI, HealthTech"
        )

        submitted = st.form_submit_button(
            "Create Profile"
        )

    if submitted:

        skills = list(dict.fromkeys(
            s.strip()
            for s in skills_text.split(",")
            if s.strip()
        ))

        interests = list(dict.fromkeys(
            s.strip()
            for s in interests_text.split(",")
            if s.strip()
        ))

        if not name.strip() or not skills:
            st.error(
                "Name and at least one skill are required."
            )

        else:
            try:
                new_id = create_user_profile(
                    name.strip(),
                    role,
                    skills,
                    interests
                )

                st.success(
                    f"Profile created successfully! "
                    f"User ID: {new_id}"
                )

            except Exception:
                st.error(
                    "Could not create profile. "
                    "Check application logs."
                )

# COMMUNITYGRAPH AI - Graph Recommendation

import networkx as nx
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity


def graph_ai_recommend(problem_id):

    # Read graph structure, excluding saved predictions
    edges = run_query("""
        MATCH (a)-[r]->(b)
        WHERE type(r) IN [
            'HAS_SKILL',
            'INTERESTED_IN',
            'REQUIRES',
            'IN_SECTOR',
            'OWNS'
        ]
        RETURN
            elementId(a) AS source,
            elementId(b) AS target
    """)

    G = nx.Graph()

    for edge in edges:
        G.add_edge(edge["source"], edge["target"])

    if G.number_of_nodes() < 3:
        return []

    nodes = list(G.nodes())
    A = nx.to_numpy_array(G, nodelist=nodes)

    features = A + A @ A

    svd = TruncatedSVD(
        n_components=min(8, len(nodes) - 1),
        random_state=42
    )

    embeddings = svd.fit_transform(features)

    embedding_map = dict(zip(nodes, embeddings))

    # Problem details
    problem_rows = run_query("""
        MATCH (p:Problem {id: $problem_id})

        OPTIONAL MATCH (p)-[:REQUIRES]->(s:Skill)
        WITH p, collect(DISTINCT s.name) AS skills

        OPTIONAL MATCH (p)-[:IN_SECTOR]->(i:Sector)
        WITH p, skills, head(collect(DISTINCT i.name)) AS industry

        OPTIONAL MATCH (owner:User)-[:OWNS]->(p)

        RETURN
            elementId(p) AS node_id,
            skills,
            industry,
            head(collect(DISTINCT owner.id)) AS owner_id
    """, problem_id=problem_id)

    if not problem_rows:
        return []

    p = problem_rows[0]

    if p["node_id"] not in embedding_map:
        return []

    required = set(s for s in p["skills"] if s)

    if not required:
        return []

    # Expert details
    experts = run_query("""
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
        WITH u, collect(DISTINCT s.name) AS skills

        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Sector)

        RETURN
            elementId(u) AS node_id,
            u.id AS id,
            u.name AS name,
            u.role AS role,
            skills,
            collect(DISTINCT i.name) AS industries
    """)

    results = []

    for expert in experts:

        if expert["id"] == p["owner_id"]:
            continue

        if expert["node_id"] not in embedding_map:
            continue

        skills = set(s for s in expert["skills"] if s)

        matched = required & skills
        missing = required - skills

        # Require at least one matching skill
        if not matched:
            continue

        skill_score = len(matched) / len(required)

        industry_score = float(
            p["industry"] is not None
            and p["industry"] in expert["industries"]
        )

        similarity = float(cosine_similarity(
            [embedding_map[p["node_id"]]],
            [embedding_map[expert["node_id"]]]
        )[0][0])

        graph_score = max(0.0, min(1.0, similarity))

        hybrid_score = (
            0.50 * skill_score
            + 0.20 * industry_score
            + 0.30 * graph_score
        )

        results.append({
            "name": expert["name"],
            "role": expert["role"],
            "score": hybrid_score,
            "skills": sorted(matched),
            "missing": sorted(missing),
            "skill_contribution": 0.50 * skill_score,
            "industry_contribution": 0.20 * industry_score,
            "graph_contribution": 0.30 * graph_score
        })


    return sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )
# COMMUNITYGRAPH AI - Recommendation Interface

st.divider()
st.header("AI Expert Recommendations")

try:
    ai_problems = run_query("""
        MATCH (p:Problem)
        RETURN p.id AS id, p.name AS name
        ORDER BY name
    """)

    if ai_problems:

        options = {
            f"{p['name']} ({p['id']})": p["id"]
            for p in ai_problems
        }

        selected = st.selectbox(
            "Select a startup problem",
            list(options.keys()),
            key="ai_problem_selector"
        )

        if st.button("Find AI Matches", type="primary"):

            with st.spinner("Analyzing graph..."):

                recommendations = graph_ai_recommend(
                    options[selected]
                )

            st.session_state["ai_recommendations"] = (
                recommendations
            )
            st.session_state["ai_selected_problem"] = (
                options[selected]
            )

        if (
            st.session_state.get("ai_selected_problem")
            == options[selected]
        ):
            recommendations = st.session_state.get(
                "ai_recommendations", []
            )

            if not recommendations:
                st.info("No matching experts found.")

            for rank, expert in enumerate(
                recommendations, start=1
            ):

                with st.container(border=True):

                    st.subheader(
                        f"{rank}. {expert['name']}"
                    )

                    st.caption(expert["role"])

                    st.metric(
                        "Hybrid Match Score",
                        f"{expert['score']:.4f}"
                    )

                    st.progress(
                        max(0.0, min(1.0, expert["score"]))
                    )

                    st.write(
                        "Matching skills:",
                        ", ".join(expert["skills"])
                    )

                    st.write(
                        "Missing skills:",
                        ", ".join(expert["missing"]) or "None"
                    )

                    with st.expander(
                        "Explain AI Recommendation"
                    ):
                        st.write(
                            "Skill contribution:",
                            round(
                                expert["skill_contribution"], 4
                            )
                        )

                        st.write(
                            "Industry contribution:",
                            round(
                                expert["industry_contribution"], 4
                            )
                        )

                        st.write(
                            "Graph contribution:",
                            round(
                                expert["graph_contribution"], 4
                            )
                        )
                        st.write(
                            "Graph contribution:",
                            round(
                                expert["graph_contribution"], 4
                            )
                        )

    else:
        st.info("No startup problems found.")

except Exception as error:
    st.error("AI recommendations could not be loaded.")
    st.error(f"Error type: {type(error).__name__}")

# COMMUNITYGRAPH - AI Problem Analyzer

st.divider()
st.header("AI Problem Analyzer")

st.write(
    "Describe your startup problem. "
    "AI will identify the industry, "
    "required skills and expert roles."
)

problem_text = st.text_area(
    "Describe your startup problem",
    placeholder=(
        "We are building an AI-powered logistics "
        "platform to predict delivery delays..."
    ),
    height=150,
    key="ai_problem_text"
)

if st.button("Analyze with AI", key="analyze_ai_button"):

    if len(problem_text.strip()) < 20:
        st.warning("Please enter a longer description.")

    else:
        with st.spinner("AI is analyzing your problem..."):
            try:
                analysis_result = analyze_startup_problem(
                    problem_text.strip()
                )
                st.session_state["problem_analysis"] = (
                    analysis_result
                )
            except Exception as error:
    st.error("AI analysis failed.")

    # Show only the exception type publicly
    st.write("Error type:", type(error).__name__)

    # Full details stay in server logs
    import logging
    logging.exception("AI Problem Analyzer failed")

if "problem_analysis" in st.session_state:

    result = st.session_state["problem_analysis"]

    st.subheader("AI Analysis Results")

    st.write("**Industry:**", result["industry"])

    st.write("**Required Skills:**")
    for skill in result["required_skills"]:
        st.write("•", skill)

    st.write("**Recommended Expert Roles:**")
    for role in result["expert_roles"]:
        st.write("•", role)

    st.info(
        "This is an AI-generated draft. "
        "Review the results before saving."
    )
