import os
import ssl
import certifi

from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / ".env")


def get_experts():
    uri = os.environ["NEO4J_URI"].strip()

    if uri.startswith("neo4j+s://"):
        uri = "neo4j://" + uri[len("neo4j+s://"):]

    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with GraphDatabase.driver(
        uri,
        auth=(
            os.environ["NEO4J_USERNAME"],
            os.environ["NEO4J_PASSWORD"]
        ),
        ssl_context=context,
        connection_timeout=10,
    ) as driver:
        records, _, _ = driver.execute_query("""
            MATCH (u:User)
            OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Skill)
            OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Sector)
            RETURN
                u.id AS id,
                u.name AS name,
                u.role AS role,
                collect(DISTINCT s.name) AS skills,
                collect(DISTINCT i.name) AS industries
        """)

        return [dict(record) for record in records]
