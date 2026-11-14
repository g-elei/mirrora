// Clear existing user data (if any)
MATCH (u:User {name: "Bishow"}) DETACH DELETE u;

// Create the User and their baseline Profile
CREATE (u:User {name: "Bishow", goal: "Graduate School", value: "Success"})
CREATE (s1:Struggle {name: "Academic Pressure"})
CREATE (u)-[:FACES]->(s1)

// Add a sample historical check-in
CREATE (c1:CheckIn {text: "I feel like everyone is getting internships and I'm falling behind.", date: "2026-11-14"})
MERGE (e1:Emotion {name: "envy"})
MERGE (e2:Emotion {name: "anxiety"})
CREATE (u)-[:MADE_CHECKIN]->(c1)
CREATE (c1)-[:FELT]->(e1)
CREATE (c1)-[:FELT]->(e2)
CREATE (c1)-[:RELATES_TO]->(s1)
RETURN u, c1;