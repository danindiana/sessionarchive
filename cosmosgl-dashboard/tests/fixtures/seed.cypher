CREATE (:Paper {name: "Test Paper", pdf_path: "/nonexistent/paper.pdf", motivation: "Testing the dashboard end-to-end", page_count: 12});
CREATE (:Concept {name: "Test Concept", definition: "A concept node used only for dashboard container tests"});
CREATE (:Theorem {name: "Isolated Theorem", statement: "Has no edges, so no fx/fy is ever set on it"});
MATCH (p:Paper {name: "Test Paper"}), (c:Concept {name: "Test Concept"})
CREATE (p)-[:MENTIONS]->(c);
