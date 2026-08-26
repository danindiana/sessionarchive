// Small illustrative demo graph for HOWTO.md's cold-start walkthrough — not a test
// fixture (see ../tests/fixtures/seed.cypher for that). Spans all six node types
// the dashboard color/size-codes, with enough edges to see the GPU layout do
// something interesting. Load with:
//
//   docker compose exec -T neo4j cypher-shell -u neo4j -p password123 < examples/demo_seed.cypher
//
// Wipes any existing graph in the target Neo4j first, so this is safe to re-run.

MATCH (n) DETACH DELETE n;

CREATE (:Paper {name: "Attention Is All You Need", motivation: "Sequence transduction without recurrence or convolutions.", pdf_path: "/nonexistent/attention.pdf", page_count: 15});
CREATE (:Paper {name: "Deep Residual Learning", motivation: "Residual connections ease training of very deep networks.", pdf_path: "/nonexistent/resnet.pdf", page_count: 12});
CREATE (:Paper {name: "GPU-Accelerated Graph Layout", motivation: "ForceAtlas2 on cuGraph for real-time visualization.", pdf_path: "/nonexistent/gpu-layout.pdf", page_count: 9});
CREATE (:Paper {name: "Contrastive Representation Learning", motivation: "Learning embeddings via contrastive objectives.", pdf_path: "/nonexistent/contrastive.pdf", page_count: 11});
CREATE (:Paper {name: "Efficient Transformers Survey", motivation: "A survey of efficient attention mechanisms.", pdf_path: "/nonexistent/efficient-transformers.pdf", page_count: 22});

CREATE (:Concept {name: "Self-Attention", definition: "Weighting the relevance of every element in a sequence to every other element."});
CREATE (:Concept {name: "Backpropagation", definition: "Reverse-mode automatic differentiation used to train neural networks."});
CREATE (:Concept {name: "Embedding Space", definition: "A learned vector space where semantic similarity corresponds to geometric proximity."});
CREATE (:Concept {name: "Gradient Descent", definition: "Iterative first-order optimization by following the negative gradient."});
CREATE (:Concept {name: "Normalization", definition: "Rescaling activations to stabilize and speed up training."});
CREATE (:Concept {name: "Graph Sampling", definition: "Selecting a representative subgraph to make computation on large graphs tractable."});

CREATE (:Theorem {name: "Universal Approximation Theorem", statement: "A feedforward network with a single hidden layer can approximate any continuous function, given enough width."});
CREATE (:Theorem {name: "No Free Lunch Theorem", statement: "No optimization algorithm outperforms all others across every possible problem."});

CREATE (:Algorithm {name: "ForceAtlas2", pseudocode: "function force_atlas2(graph, max_iter=500): ...", invariant: "Repulsion between all nodes, attraction along edges, converges to a stable layout."});
CREATE (:Algorithm {name: "Adam Optimizer", pseudocode: "function adam(params, grads, lr=0.001): ...", invariant: "Maintains per-parameter running averages of gradient and squared gradient."});
CREATE (:Algorithm {name: "PageRank", pseudocode: "function pagerank(graph, damping=0.85): ...", invariant: "Rank is redistributed proportionally along outgoing edges each iteration."});

CREATE (:CodeSnippet {name: "cuGraph force_atlas2 call", language: "Python", code: "cugraph.force_atlas2(G, max_iter=500, strong_gravity_mode=False)"});
CREATE (:CodeSnippet {name: "Cosmos point-position shader", language: "GLSL", code: "vec4 pointPosition = texture(positionsTexture, uv);"});

CREATE (:Diagram {name: "Transformer Architecture", dot_src: "digraph { encoder -> decoder }", svg_path: "diagrams/transformer.svg"});
CREATE (:Diagram {name: "Neo4j Bolt Protocol Flow", dot_src: "digraph { client -> bolt -> server }", svg_path: "diagrams/bolt_flow.svg"});

// Papers cite/use concepts, algorithms, diagrams, and code
MATCH (p:Paper {name: "Attention Is All You Need"}), (c:Concept {name: "Self-Attention"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Attention Is All You Need"}), (c:Concept {name: "Embedding Space"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Attention Is All You Need"}), (d:Diagram {name: "Transformer Architecture"}) CREATE (p)-[:ILLUSTRATED_BY]->(d);
MATCH (p:Paper {name: "Deep Residual Learning"}), (c:Concept {name: "Backpropagation"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Deep Residual Learning"}), (c:Concept {name: "Gradient Descent"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Deep Residual Learning"}), (c:Concept {name: "Normalization"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "GPU-Accelerated Graph Layout"}), (a:Algorithm {name: "ForceAtlas2"}) CREATE (p)-[:USES]->(a);
MATCH (p:Paper {name: "GPU-Accelerated Graph Layout"}), (c:Concept {name: "Graph Sampling"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "GPU-Accelerated Graph Layout"}), (cs:CodeSnippet {name: "cuGraph force_atlas2 call"}) CREATE (p)-[:IMPLEMENTED_IN]->(cs);
MATCH (p:Paper {name: "GPU-Accelerated Graph Layout"}), (cs:CodeSnippet {name: "Cosmos point-position shader"}) CREATE (p)-[:IMPLEMENTED_IN]->(cs);
MATCH (p:Paper {name: "Contrastive Representation Learning"}), (c:Concept {name: "Embedding Space"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Contrastive Representation Learning"}), (a:Algorithm {name: "Adam Optimizer"}) CREATE (p)-[:USES]->(a);
MATCH (p:Paper {name: "Efficient Transformers Survey"}), (c:Concept {name: "Self-Attention"}) CREATE (p)-[:MENTIONS]->(c);
MATCH (p:Paper {name: "Efficient Transformers Survey"}), (p2:Paper {name: "Attention Is All You Need"}) CREATE (p)-[:MENTIONS]->(p2);

// Theorems relate back to the concepts they formalize
MATCH (t:Theorem {name: "Universal Approximation Theorem"}), (c:Concept {name: "Embedding Space"}) CREATE (c)-[:RELATES_TO]->(t);
MATCH (t:Theorem {name: "No Free Lunch Theorem"}), (a:Algorithm {name: "Adam Optimizer"}) CREATE (a)-[:RELATES_TO]->(t);
MATCH (t:Theorem {name: "No Free Lunch Theorem"}), (a:Algorithm {name: "PageRank"}) CREATE (a)-[:RELATES_TO]->(t);

// A few concept-to-concept relationships so the graph isn't purely star-shaped
MATCH (a:Concept {name: "Backpropagation"}), (b:Concept {name: "Gradient Descent"}) CREATE (a)-[:RELATES_TO]->(b);
MATCH (a:Concept {name: "Gradient Descent"}), (b:Concept {name: "Normalization"}) CREATE (a)-[:RELATES_TO]->(b);
MATCH (a:Concept {name: "Self-Attention"}), (b:Concept {name: "Embedding Space"}) CREATE (a)-[:RELATES_TO]->(b);
MATCH (a:Algorithm {name: "PageRank"}), (c:Concept {name: "Graph Sampling"}) CREATE (a)-[:RELATES_TO]->(c);
