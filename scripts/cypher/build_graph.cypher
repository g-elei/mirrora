// Clear existing data
MATCH (n) DETACH DELETE n;

// 1. Create Authors
CREATE (a1:Author {name: "F. Scott Fitzgerald"})
CREATE (a2:Author {name: "Fyodor Dostoevsky"})
CREATE (a3:Author {name: "Virginia Woolf"})

// 2. Create Books
CREATE (b1:Book {title: "The Great Gatsby", year: 1925})
CREATE (b2:Book {title: "Notes from Underground", year: 1864})
CREATE (b3:Book {title: "Mrs Dalloway", year: 1925})

// 3. Connect Authors to Books
CREATE (a1)-[:WROTE]->(b1)
CREATE (a2)-[:WROTE]->(b2)
CREATE (a3)-[:WROTE]->(b3)

// 4. Create Passages and connect them to Books, Themes, and Emotions
CREATE (p1:Passage {id: "p1", text: "He had spent years comparing himself to men who seemed to rise without effort, and the comparison had hollowed him out."})
CREATE (b1)-[:CONTAINS]->(p1)
MERGE (t1:Theme {name: "ambition"})
MERGE (t2:Theme {name: "identity"})
MERGE (e1:Emotion {name: "envy"})
MERGE (e2:Emotion {name: "self_doubt"})
CREATE (p1)-[:EXPLORES]->(t1)
CREATE (p1)-[:EXPLORES]->(t2)
CREATE (p1)-[:EXPRESSES]->(e1)
CREATE (p1)-[:EXPRESSES]->(e2)

CREATE (p2:Passage {id: "p2", text: "I am a sick man... I am a spiteful man. I am an unattractive man. I believe my liver is diseased."})
CREATE (b2)-[:CONTAINS]->(p2)
MERGE (t3:Theme {name: "failure"})
MERGE (e3:Emotion {name: "frustration"})
CREATE (p2)-[:EXPLORES]->(t3)
CREATE (p2)-[:EXPRESSES]->(e3)

CREATE (p3:Passage {id: "p3", text: "She felt very young; at the same time unspeakably aged. She sliced like a knife through everything; at the same time was outside, looking on."})
CREATE (b3)-[:CONTAINS]->(p3)
MERGE (t4:Theme {name: "loneliness"})
MERGE (e4:Emotion {name: "exhaustion"})
CREATE (p3)-[:EXPLORES]->(t4)
CREATE (p3)-[:EXPRESSES]->(e4)

RETURN p1, p2, p3;