
# CommunityGraph v0.7 - Supabase Authentication
import streamlit as st
from supabase import create_client

@st.cache_resource

def get_supabase():
    if "cg_supabase_client" not in st.session_state:
        st.session_state["cg_supabase_client"] = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_ANON_KEY"]
        )

    return st.session_state["cg_supabase_client"]

def auth_screen():
    st.title("CommunityGraph")
    st.caption("Connect founders with the right experts.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login = st.form_submit_button("Login")

        if login:
            try:
                result = get_supabase().auth.sign_in_with_password({
                    "email": email.strip(),
                    "password": password
                })
                if result.session:
                    st.session_state["cg_access_token"] = result.session.access_token
                    st.session_state["cg_refresh_token"] = result.session.refresh_token
                    st.rerun()
            except Exception:
                st.error("Login failed. Check your credentials.")

    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email_new = st.text_input("Email Address")
            password_new = st.text_input("Create Password", type="password")
            role = st.selectbox("Role", ["Founder", "Expert"])
            signup = st.form_submit_button("Create Account")

        if signup:
            if not name.strip() or not email_new.strip() or len(password_new) < 8:
                st.error("Enter your name, email and a password of at least 8 characters.")
            else:
                try:
                    get_supabase().auth.sign_up({
                        "email": email_new.strip(),
                        "password": password_new,
                        "options": {
                            "data": {
                                "full_name": name.strip(),
                                "role": role
                            }
                        }
                    })
                    st.success("Registration submitted. Check your email for confirmation.")
                except Exception:
                    st.error("Registration could not be completed.")

if "cg_access_token" not in st.session_state:
    auth_screen()
    st.stop()

try:
    auth_client = get_supabase()
    auth_client.auth.set_session(
        st.session_state["cg_access_token"],
        st.session_state["cg_refresh_token"]
    )
    authenticated_user = auth_client.auth.get_user().user
    if authenticated_user is None:
        raise ValueError("Invalid session")
    current_session = auth_client.auth.get_session()
    if current_session:
        st.session_state["cg_access_token"] = current_session.access_token
        st.session_state["cg_refresh_token"] = current_session.refresh_token
except Exception:
    st.session_state.pop("cg_access_token", None)
    st.session_state.pop("cg_refresh_token", None)
    st.warning("Your session has expired. Please log in again.")
    st.stop()

with st.sidebar:
    st.write("Logged in:", authenticated_user.email)
    if st.button("Logout"):
        auth_client.auth.sign_out()
        st.session_state.pop("cg_access_token", None)
        st.session_state.pop("cg_refresh_token", None)
        st.rerun()

# Existing CommunityGraph application continues below.

# CommunityGraph v0.7 - My Profile
def show_my_profile():
    st.subheader("My Profile")

    user_id = str(authenticated_user.id)

    try:
        result = (
            auth_client.table("profiles")
            .select("full_name, role, bio, industry")
            .eq("id", user_id)
            .single()
            .execute()
        )
        profile = result.data or {}
    except Exception:
        st.error("Profile could not be loaded.")
        return

    st.caption(f"Account: {authenticated_user.email}")
    st.write("Current role:", profile.get("role", "Member"))

    with st.form("cg_profile_form"):
        full_name = st.text_input(
            "Full Name",
            value=profile.get("full_name") or ""
        )

        industry = st.text_input(
            "Industry / Field",
            value=profile.get("industry") or ""
        )

        bio = st.text_area(
            "Bio / Skills / Interests",
            value=profile.get("bio") or ""
        )

        save_profile = st.form_submit_button(
            "Save Profile"
        )

    if save_profile:
        if not full_name.strip():
            st.error("Full Name cannot be empty.")
            return

        try:
            auth_client.table("profiles").update({
                "full_name": full_name.strip(),
                "industry": industry.strip(),
                "bio": bio.strip()
            }).eq("id", user_id).execute()

            st.success("Profile updated successfully.")
            st.rerun()

        except Exception:
            st.error("Profile update failed.")


with st.sidebar:
    st.divider()
    show_profile = st.checkbox(
        "My Profile",
        key="cg_show_my_profile"
    )

if show_profile:
    show_my_profile()
    st.stop()

# End of My Profile


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

import json
from groq import Groq



def analyze_startup_problem(description):
    client = Groq(
        api_key=st.secrets["GROQ_API_KEY"],
        timeout=30.0
    )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze startup problems. "
                    "Return valid JSON containing: "
                    "industry, required_skills, expert_roles. "
                    "Industry must be a string. "
                    "Skills and roles must be lists of strings. "
                    "Do not include markdown."
                )
            },
            {
                "role": "user",
                "content": description
            }
        ],
        temperature=0,
        max_completion_tokens=700,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content

    if not raw:
        raise ValueError("Empty AI response")

    result = json.loads(raw)

    if not isinstance(result, dict):
        raise ValueError("Invalid JSON object")

    if not isinstance(result.get("industry"), str):
        raise ValueError("Invalid industry")

    for field in ["required_skills", "expert_roles"]:
        values = result.get(field)

        if not isinstance(values, list):
            raise ValueError(f"Invalid {field}")

        if not all(isinstance(x, str) for x in values):
            raise ValueError(f"Invalid {field} values")

    return result


def recommend_from_ai_analysis(analysis):

    experts = run_query("""
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
        WITH u, collect(DISTINCT s.name) AS skills

        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Sector)

        RETURN
            u.id AS id,
            u.name AS name,
            u.role AS role,
            skills,
            collect(DISTINCT i.name) AS industries
    """)

    required = {
        s.strip().casefold()
        for s in analysis["required_skills"]
    }

    industry = analysis["industry"].strip().casefold()

    recommendations = []

    for expert in experts:
        skills = {
            s.strip().casefold()
            for s in expert["skills"] if s
        }

        matched = required & skills

        if not matched:
            continue

        skill_score = len(matched) / len(required)

        industry_score = float(
            industry in {
                i.strip().casefold()
                for i in expert["industries"] if i
            }
        )

        score = (
            0.75 * skill_score
            + 0.25 * industry_score
        )

        recommendations.append({
            "name": expert["name"],
            "role": expert["role"],
            "score": round(score, 4),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(required - skills)
        })

    return sorted(
        recommendations,
        key=lambda x: x["score"],
        reverse=True
    )

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
                st.session_state["cg_analyzed_description"] = problem_text.strip()
                st.session_state.pop("ai_expert_matches", None)
                st.session_state.pop("cg_saved_problem_id", None)
                st.session_state.pop("cg_graph_matches", None)
                st.session_state.pop("cg_graph_error", None)
                st.success("AI analysis completed!")

            except Exception as error:
                st.error("AI analysis failed.")
                st.write(
                    "Error type:",
                    type(error).__name__
                )

                import logging
                logging.exception(
                    "AI Problem Analyzer failed"
                )



if "problem_analysis" in st.session_state:
    analysis_data = st.session_state["problem_analysis"]

    st.write(
        "Analysis data type:",
        type(analysis_data).__name__
    )

    if isinstance(analysis_data, dict):
        st.subheader("AI Analysis Results")

        st.write(
            "**Industry:**",
            analysis_data.get("industry", "Unknown")
        )

        st.write("**Required Skills:**")
        for skill in analysis_data.get("required_skills", []):
            st.write("•", skill)

        st.write("**Recommended Expert Roles:**")
        for role in analysis_data.get("expert_roles", []):
            st.write("•", role)

    else:
        st.error(
            "Invalid AI analysis data. "
            "Please analyze the problem again."
        )



# COMMUNITYGRAPH - AI Expert Matching

st.divider()
st.subheader("Find Experts for Your AI-Analyzed Problem")

if "problem_analysis" in st.session_state:

    analysis = st.session_state["problem_analysis"]

    if st.button(
        "Find Matching Experts",
        key="find_ai_experts"
    ):
        with st.spinner("Finding matching experts..."):
            try:
                matches = recommend_from_ai_analysis(
                    analysis
                )

                st.session_state["ai_expert_matches"] = (
                    matches
                )

                st.success("Expert matching completed!")

            except Exception:
                st.error(
                    "Expert matching failed. "
                    "Check application logs."
                )
                import logging
                logging.exception(
                    "AI expert matching failed"
                )

    if "ai_expert_matches" in st.session_state:

        matches = st.session_state["ai_expert_matches"]

        if not matches:
            st.info(
                "No matching experts found for "
                "the extracted skills."
            )

        for rank, expert in enumerate(matches, start=1):

            with st.container(border=True):

                st.subheader(
                    f"{rank}. {expert['name']}"
                )

                st.caption(expert["role"])

                st.metric(
                    "Skill & Industry Match Score",
                    f"{expert['score']:.4f}"
                )

                st.write(
                    "**Matching Skills:**",
                    ", ".join(expert["matched_skills"])
                )

                st.write(
                    "**Missing Skills:**",
                    ", ".join(expert["missing_skills"])
                    or "None"
                )

else:
    st.info(
        "Analyze a startup problem first "
        "to find matching experts."
    )


# COMMUNITYGRAPH v0.6 (dev) - AI analysis -> Neo4j -> Graph AI
# Existing analyzer, manual problem creation and recommendation views remain unchanged.

def save_ai_analyzed_problem(owner_id, title, description, analysis):
    """Persist an AI-analyzed problem with the graph relationships Graph AI needs."""
    industry = analysis.get("industry", "").strip()
    skills = list(dict.fromkeys(
        value.strip() for value in analysis.get("required_skills", [])
        if isinstance(value, str) and value.strip()
    ))
    if not owner_id or not title.strip() or len(description.strip()) < 20:
        raise ValueError("Owner, title and a description of at least 20 characters are required.")
    if not industry or not skills:
        raise ValueError("AI analysis must include an industry and at least one skill.")

    new_problem_id = "p_" + uuid.uuid4().hex[:12]
    saved = run_query("""
        MATCH (owner:User {id: $owner_id})
        WHERE owner.role = 'Founder'
        CREATE (p:Problem {
            id: $problem_id,
            name: $title,
            description: $description,
            sector: $industry
        })
        CREATE (owner)-[:OWNS]->(p)
        MERGE (sector:Sector {id: $sector_id})
        ON CREATE SET sector.name = $industry, sector.type = 'Sector'
        CREATE (p)-[:IN_SECTOR]->(sector)
        WITH p
        UNWIND $skills AS skill_name
        MERGE (skill:Skill {id: 'skill:' + skill_name})
        ON CREATE SET skill.name = skill_name, skill.type = 'Skill'
        MERGE (p)-[:REQUIRES]->(skill)
        RETURN DISTINCT p.id AS id
    """,
        owner_id=owner_id,
        problem_id=new_problem_id,
        title=title.strip(),
        description=description.strip(),
        industry=industry,
        sector_id="sector:" + industry,
        skills=skills
    )
    if not saved:
        raise ValueError("No Founder profile was found for the selected owner.")
    return saved[0]["id"]


st.divider()
st.header("AI to Graph AI - End-to-End Matching (dev)")
st.caption("Analyze a problem above, then save it as a graph and find hybrid matches.")

cg_analysis = st.session_state.get("problem_analysis")
if not isinstance(cg_analysis, dict):
    st.info("First run Analyze with AI above.")
else:
    st.write("**Detected industry:**", cg_analysis.get("industry", ""))
    st.write("**Detected skills:**", ", ".join(cg_analysis.get("required_skills", [])))
    cg_admin_password = st.text_input(
        "Admin password for AI problem saving",
        type="password",
        key="cg_ai_save_admin_password"
    )
    cg_expected_password = st.secrets.get("ADMIN_PASSWORD", "")
    cg_is_admin = bool(
        cg_expected_password
        and hmac.compare_digest(cg_admin_password, cg_expected_password)
    )

    if not cg_is_admin:
        st.info("Admin access is required to save AI-analyzed problems.")
    else:
        try:
            cg_founders = run_query("""
                MATCH (u:User)
                WHERE u.role = 'Founder'
                RETURN u.id AS id, u.name AS name
                ORDER BY name
            """)
            if not cg_founders:
                st.warning("Create a Founder profile before saving a problem.")
            else:
                cg_founder_options = {
                    f"{f['name']} ({f['id']})": f["id"] for f in cg_founders
                }
                with st.form("cg_ai_graph_save_form"):
                    cg_title = st.text_input("Problem title", key="cg_ai_graph_title")
                    cg_owner = st.selectbox(
                        "Problem owner", list(cg_founder_options),
                        key="cg_ai_graph_owner"
                    )
                    st.caption("The current AI problem description will be saved.")
                    cg_submit = st.form_submit_button("Save to Neo4j and run Graph AI")

                if cg_submit:
                    try:
                        with st.spinner("Saving problem and calculating graph matches..."):
                            cg_problem_id = save_ai_analyzed_problem(
                                cg_founder_options[cg_owner],
                                cg_title,
                                st.session_state.get("cg_analyzed_description", ""),
                                cg_analysis
                            )
                            st.session_state["cg_saved_problem_id"] = cg_problem_id
                            st.session_state.pop("cg_graph_error", None)
                            try:
                                st.session_state["cg_graph_matches"] = graph_ai_recommend(
                                    cg_problem_id
                                )
                            except Exception as graph_error:
                                # The Neo4j write has already succeeded; do not retry it.
                                st.session_state["cg_graph_matches"] = []
                                st.session_state["cg_graph_error"] = type(graph_error).__name__
                                import logging
                                logging.exception("Graph AI failed after problem was saved")
                        st.success("Problem saved to Neo4j.")
                    except Exception as save_error:
                        st.error("Could not save AI-analyzed problem.")
                        st.write("Error type:", type(save_error).__name__)
                        import logging
                        logging.exception("AI problem save failed")
        except Exception as founder_error:
            st.error("Could not load Founder profiles.")
            st.write("Error type:", type(founder_error).__name__)

    if st.session_state.get("cg_saved_problem_id"):
        st.write("**Saved problem ID:**", st.session_state["cg_saved_problem_id"])
        if st.session_state.get("cg_graph_error"):
            st.warning(
                "Problem was saved, but Graph AI could not finish. "
                "Error type: " + st.session_state["cg_graph_error"]
            )
        else:
            cg_matches = st.session_state.get("cg_graph_matches", [])
            if not cg_matches:
                st.info("No hybrid graph matches were found for this problem.")
            for rank, expert in enumerate(cg_matches, start=1):
                with st.container(border=True):
                    st.subheader(f"{rank}. {expert['name']}")
                    st.caption(expert.get("role", ""))
                    st.metric("Hybrid Match Score", f"{expert['score']:.4f}")
                    st.progress(max(0.0, min(1.0, expert["score"])))
                    st.write("Matching skills:", ", ".join(expert["skills"]))
                    st.write("Missing skills:", ", ".join(expert["missing"]) or "None")
                    with st.expander("Explain AI Recommendation"):
                        st.write("Skill contribution:", round(expert["skill_contribution"], 4))
                        st.write("Industry contribution:", round(expert["industry_contribution"], 4))
                        st.write("Graph contribution:", round(expert["graph_contribution"], 4))

# ==========================================================
# CommunityGraph v0.7 - Supabase / Neo4j User Sync
# ==========================================================

def cg_sync_authenticated_user():
    """Synchronize the verified Supabase user with Neo4j."""

    user_id = str(authenticated_user.id)

    try:
        # Load the profile using the authenticated session.
        response = (
            auth_client.table("profiles")
            .select("full_name, role, bio, industry")
            .eq("id", user_id)
            .single()
            .execute()
        )

        profile = response.data

        if not profile:
            return False, "Supabase profile not found."

        # Use an explicit transaction with parameters.
        # Never match existing demo users by name or email.
        query = """
        MERGE (u:User {auth_id: $auth_id})
        ON CREATE SET
            u.source = 'supabase',
            u.created_at = datetime()
        SET
            u.full_name = $full_name,
            u.role = $role,
            u.bio = $bio,
            u.industry = $industry,
            u.updated_at = datetime()
        RETURN u.auth_id AS auth_id
        """

        with get_driver().session(
            database=get_database()
        ) as session:
            record = session.run(
                query,
                auth_id=user_id,
                full_name=profile.get("full_name") or "",
                role=profile.get("role") or "Founder",
                bio=profile.get("bio") or "",
                industry=profile.get("industry") or ""
            ).single()

        if not record or record["auth_id"] != user_id:
            return False, "Neo4j verification failed."

        return True, "User synchronized successfully."

    except Exception as exc:
        return False, f"Synchronization failed: {type(exc).__name__}"


# Temporary integration test panel.
# Remove this panel after verification.
if "cg_access_token" in st.session_state:
    with st.sidebar:
        st.divider()
        st.caption("v0.7 Integration Test")

        if st.button(
            "Sync My Profile to Neo4j",
            key="cg_sync_neo4j"
        ):
            success, message = cg_sync_authenticated_user()

            if success:
                st.success(message)
            else:
                st.error(message)

# ==========================================================
# End of Supabase / Neo4j User Sync
# ==========================================================
