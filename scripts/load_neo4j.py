import json
from pathlib import Path
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", "password"))

def load(path="data/seed/passages.json"):
    passages = json.loads(Path(path).read_text(encoding="utf-8"))
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")  # clean slate
            for p in passages:
                s.run("""
                    MERGE (p:Passage {id: $id})
                    SET p.text = $text, p.book = $book, p.location = $location
                """, **p)
                
                for theme in p.get("themes", []):
                    s.run("""
                        MATCH (p:Passage {id: $id})
                        MERGE (t:Theme {name: $theme})
                        MERGE (p)-[:EXPLORES]->(t)
                    """, id=p["id"], theme=theme)
                for emo in p.get("expresses", []):
                    s.run("""
                        MATCH (p:Passage {id: $id})
                        MERGE (e:Emotion {name: $emo})
                        MERGE (p)-[:EXPRESSES]->(e)
                    """, id=p["id"], emo=emo)
                for emo in p.get("addresses", []):
                    s.run("""
                        MATCH (p:Passage {id: $id})
                        MERGE (e:Emotion {name: $emo})
                        MERGE (p)-[:ADDRESSES]->(e)
                    """, id=p["id"], emo=emo)
    print(f"Loaded {len(passages)} passages")

if __name__ == "__main__":
    load()