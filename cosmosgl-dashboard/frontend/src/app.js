// CosmosGL dashboard frontend — fetches the graph from cosmos_server.py's
// /api/graph, hands typed arrays to @cosmos.gl/graph for a static
// (enableSimulation: false) GPU-rendered layout, and wires up node detail
// modals + source-PDF links via /api/node/<id> and /pdf/<id>.
//
// Reconstructed from paper_processor/neo4j_viz/cosmos_bundle.js — the
// pre-built esbuild output that shipped without its source ever being
// committed. Behavior (colors, sizes, double-click threshold, detail field
// layout) is preserved exactly; only names and structure were restored.
import { Graph } from "@cosmos.gl/graph";

const NODE_COLORS = {
  Paper: "#ff6b6b",
  Concept: "#4dabf7",
  Theorem: "#ffd43b",
  Algorithm: "#69db7c",
  CodeSnippet: "#da77f2",
  Diagram: "#ff922b",
};
const DEFAULT_COLOR = "#adb5bd";

const NODE_SIZES = {
  Paper: 9,
  Concept: 5,
  Theorem: 5,
  Algorithm: 5,
  CodeSnippet: 4,
  Diagram: 4,
};
const DEFAULT_SIZE = 3;

const DOUBLE_CLICK_MS = 400;

// Ordered (label, propKey, opts) field lists per node type, rendered in the
// detail modal. Any other own property not listed here (and not in
// OMITTED_KEYS) is appended afterwards in insertion order.
const DETAIL_FIELDS = {
  Paper: [
    ["Motivation & Problem", "motivation"],
    ["Methodology", "methodology"],
    ["Key Contributions", "contributions"],
    ["Limitations", "limitations"],
    ["Significance", "significance"],
    ["Extras", "extras"],
    ["Page Count", "page_count"],
    ["Processed At", "processed_at"],
    ["Source PDF Path", "pdf_path"],
  ],
  Concept: [["Definition", "definition"]],
  Theorem: [["Statement", "statement"]],
  Algorithm: [
    ["Pseudocode", "pseudocode", { pre: true }],
    ["Invariant", "invariant"],
  ],
  CodeSnippet: [
    ["Language", "language"],
    ["Code", "code", { pre: true }],
  ],
  Diagram: [
    ["Graphviz Source", "dot_src", { pre: true }],
    ["SVG Path (relative to its dataset's _processed/)", "svg_path"],
  ],
};

// fx/fy are layout coordinates, not content; name/title are already shown
// in the modal header — neither belongs in the property list body.
const OMITTED_KEYS = new Set(["fx", "fy", "name", "title"]);

function hexToRgba(hex, alpha = 1) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, alpha];
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function renderLegend(legendEl) {
  legendEl.innerHTML = Object.entries(NODE_COLORS)
    .map(([type, color]) => `<div class="legend-row"><span class="swatch" style="background:${color}"></span>${type}</div>`)
    .join("");
}

function renderNodeDetail(type, props, nodeId) {
  const title = escapeHtml(props.name ?? props.title ?? `${type} #?`);
  const fields = DETAIL_FIELDS[type] || [];
  const knownKeys = new Set(fields.map(([, key]) => key));

  let body = fields
    .map(([label, key, opts]) => {
      const value = props[key];
      if (value == null || value === "") return "";
      const rendered = opts?.pre ? `<pre>${escapeHtml(value)}</pre>` : `<p>${escapeHtml(value)}</p>`;
      return `<div class="detail-field"><h3>${escapeHtml(label)}</h3>${rendered}</div>`;
    })
    .join("");

  const extraEntries = Object.entries(props).filter(([key]) => !OMITTED_KEYS.has(key) && !knownKeys.has(key));
  if (extraEntries.length) {
    body += extraEntries
      .map(([key, value]) => `<div class="detail-field"><h3>${escapeHtml(key)}</h3><p>${escapeHtml(value)}</p></div>`)
      .join("");
  }

  const pdfButton =
    type === "Paper"
      ? `<a class="pdf-button" href="/pdf/${nodeId}" target="_blank" rel="noopener">Open source PDF ↗</a>`
      : "";

  return `
    <div class="detail-header">
      <span class="detail-type" style="color:${NODE_COLORS[type] || DEFAULT_COLOR}">${escapeHtml(type)}</span>
      <h2>${title}</h2>
      ${pdfButton}
    </div>
    <div class="detail-body">${body || "<p>No additional properties stored.</p>"}</div>
  `;
}

async function main() {
  const statusEl = document.getElementById("status");
  const legendEl = document.getElementById("legend");
  const tooltipEl = document.getElementById("tooltip");
  const graphEl = document.getElementById("graph");
  const modalEl = document.getElementById("modal");
  const modalContentEl = document.getElementById("modal-content");
  const modalCloseEl = document.getElementById("modal-close");

  function closeModal() {
    modalEl.style.display = "none";
  }
  modalCloseEl.addEventListener("click", closeModal);
  modalEl.addEventListener("click", (e) => {
    if (e.target === modalEl) closeModal();
  });

  async function openNodeDetail(nodeId, type, label) {
    if (type === "Paper") window.open(`/pdf/${nodeId}`, "_blank", "noopener");
    modalEl.style.display = "flex";
    modalContentEl.innerHTML = `<div class="detail-header"><h2>${escapeHtml(label)}</h2></div><div class="detail-body"><p>Loading…</p></div>`;
    try {
      const res = await fetch(`/api/node/${nodeId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { type: detailType, props } = await res.json();
      modalContentEl.innerHTML = renderNodeDetail(detailType || type, props, nodeId);
    } catch (err) {
      modalContentEl.innerHTML = `<div class="detail-header"><h2>${escapeHtml(label)}</h2></div><div class="detail-body"><p>Failed to load details: ${escapeHtml(err.message)}</p></div>`;
    }
  }

  renderLegend(legendEl);
  statusEl.textContent = "Loading graph from Neo4j...";

  const graphRes = await fetch("/api/graph");
  if (!graphRes.ok) {
    statusEl.textContent = `Failed to load graph: ${graphRes.status}`;
    return;
  }
  const { nodes, edges } = await graphRes.json();

  const indexById = new Map();
  nodes.forEach((n, i) => indexById.set(n.id, i));

  const positions = new Float32Array(nodes.length * 2);
  const colors = new Float32Array(nodes.length * 4);
  const sizes = new Float32Array(nodes.length);
  nodes.forEach((n, i) => {
    positions[i * 2] = n.fx;
    positions[i * 2 + 1] = n.fy;
    const [r, g, b, a] = hexToRgba(NODE_COLORS[n.type] || DEFAULT_COLOR, 1);
    colors[i * 4] = r;
    colors[i * 4 + 1] = g;
    colors[i * 4 + 2] = b;
    colors[i * 4 + 3] = a;
    sizes[i] = NODE_SIZES[n.type] ?? DEFAULT_SIZE;
  });

  const rawLinks = new Float32Array(edges.length * 2);
  let linkCount = 0;
  for (const e of edges) {
    const source = indexById.get(e.source);
    const target = indexById.get(e.target);
    if (source === undefined || target === undefined) continue;
    rawLinks[linkCount * 2] = source;
    rawLinks[linkCount * 2 + 1] = target;
    linkCount++;
  }
  const links = linkCount === edges.length ? rawLinks : rawLinks.slice(0, linkCount * 2);

  let pendingClick = null;
  function handlePointClick(index) {
    const node = nodes[index];
    if (!node) return;
    const now = Date.now();
    if (pendingClick && pendingClick.index === index && now - pendingClick.time < DOUBLE_CLICK_MS) {
      pendingClick = null;
      openNodeDetail(node.id, node.type, node.label);
    } else {
      pendingClick = { index, time: now };
    }
  }

  const graph = new Graph(graphEl, {
    enableSimulation: false,
    backgroundColor: "#101014",
    pointDefaultSize: DEFAULT_SIZE,
    linkDefaultColor: "#666666",
    linkOpacity: 0.06,
    linkWidthScale: 0.5,
    renderHoveredPointRing: true,
    hoveredPointRingColor: "#ffffff",
    fitViewOnInit: true,
    fitViewPadding: 0.15,
    onPointMouseOver: (index) => {
      const node = nodes[index];
      if (!node) return;
      tooltipEl.style.display = "block";
      tooltipEl.textContent = `${node.type}: ${node.label}`;
    },
    onPointMouseOut: () => {
      tooltipEl.style.display = "none";
    },
    onPointClick: (index) => {
      if (index !== undefined) handlePointClick(index);
    },
    onMouseMove: (_x, _y, event) => {
      if (!event) return;
      tooltipEl.style.left = `${event.clientX + 12}px`;
      tooltipEl.style.top = `${event.clientY + 12}px`;
    },
  });

  graph.setPointPositions(positions);
  graph.setPointColors(colors);
  graph.setPointSizes(sizes);
  graph.setLinks(links);
  graph.render();

  statusEl.textContent = `${nodes.length.toLocaleString()} nodes / ${linkCount.toLocaleString()} edges (static GPU-precomputed layout)`;
}

main().catch((err) => {
  document.getElementById("status").textContent = `Error: ${err.message}`;
  console.error(err);
});
