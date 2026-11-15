import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def execute_cypher_file(driver, filepath: str):
    print(f"Executing Cypher script: {filepath}...")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        cypher_script = f.read()

    # Split statements by semicolon
    statements = [stmt.strip() for stmt in cypher_script.split(";") if stmt.strip()]

    with driver.session() as session:
        for idx, statement in enumerate(statements):
            try:
                session.run(statement)
                print(f"  [Success] Statement {idx + 1} executed.")
            except Exception as e:
                print(f"  [Error] Statement {idx + 1} failed: {e}")

def main():
    print(f"Connecting to Neo4j database at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected successfully!")

        # Paths to your existing Cypher scripts in the repo structure
        build_graph_path = os.path.join("scripts", "cypher", "build_graph.cypher")
        personal_graph_path = os.path.join("scripts", "cypher", "personal_graph.cypher")

        execute_cypher_file(driver, build_graph_path)
        execute_cypher_file(driver, personal_graph_path)

        print("Graph database seeding completed successfully!")
    except Exception as e:
        print(f"Failed to connect or seed Neo4j: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()