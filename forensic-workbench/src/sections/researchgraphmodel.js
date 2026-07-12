const RELATION_PHRASES = [
  ["FALSIFIES", ["falsif", "disprove", "refute", "overturn", "sink", "break the"]],
  ["RULED_OUT", ["ruled out", "rejected", "set aside", "dismissed", "alternativ"]],
  ["CONTRADICTS", ["contradic", "conflict", "inconsist"]],
  ["CHALLENGES", ["challeng", "tension", "undercut", "threaten", "weaken", "cut against", "argue against"]],
  ["SUPPORTS", ["support", "backs", "backed by", "evidence for", "holds up", "in favou", "in favor", "props up"]],
  ["REPORTS", ["reported by", "reports", "source for", "come from", "comes from", "provenance"]],
  ["DERIVES", ["rest on", "rests on", "depend", "rely", "relies", "build on", "built on", "derive", "follow from", "hinge"]],
  ["TESTS", ["would test", "discriminat", "would settle", "distinguish", "probe", "decide between"]],
  ["CONSTRAINS", ["constrain", "limit", "bound", "restrict", "govern"]],
];

const STOP_WORDS = new Set([
  "what", "which", "would", "could", "does", "the", "this", "that", "thesis", "claim", "claims",
  "about", "and", "for", "with", "are", "our", "have", "how", "why", "you", "its", "it", "is",
  "a", "an", "on", "of", "to", "me", "show", "list", "all",
]);

export function looksLikeMapQuestion(text) {
  return /^(what|which|how|where|why|show|list|does|could|would|is|are)\b/i.test(String(text || "").trim())
    || /\?\s*$/.test(String(text || ""));
}

export function interpretMapQuestion(text, presentPredicates) {
  const source = String(text || "");
  const normalized = source.toLowerCase();
  let predicate = null;
  for (const [relation, phrases] of RELATION_PHRASES) {
    if (presentPredicates.includes(relation) && phrases.some((phrase) => normalized.includes(phrase))) {
      predicate = relation;
      break;
    }
  }
  if (!predicate) return { predicate: null, keyword: source };

  const relationWords = new Set(RELATION_PHRASES.flatMap(([, phrases]) => phrases).flatMap((phrase) => phrase.split(" ")));
  const keyword = normalized.replace(/[^a-z0-9 ]+/g, " ").split(/\s+/)
    .filter((word) => word.length > 2
      && !STOP_WORDS.has(word)
      && !relationWords.has(word)
      && ![...relationWords].some((relationWord) => relationWord.length > 3 && word.startsWith(relationWord)))
    .join(" ");
  return { predicate, keyword };
}

function adjacencyFor(nodes, edges) {
  const ids = nodes.map((node) => node.id);
  const valid = new Set(ids);
  const outgoing = new Map(ids.map((id) => [id, []]));
  const incoming = new Map(ids.map((id) => [id, []]));
  const keptEdges = [];
  for (const edge of edges) {
    if (!valid.has(edge.from) || !valid.has(edge.to)) continue;
    outgoing.get(edge.from).push(edge.to);
    incoming.get(edge.to).push(edge.from);
    keptEdges.push(edge);
  }
  return { ids, outgoing, incoming, keptEdges };
}

// Iterative Kosaraju avoids recursion limits while collapsing every directed cycle to one component.
function stronglyConnectedComponents(ids, outgoing, incoming) {
  const visited = new Set();
  const finishOrder = [];
  for (const start of ids) {
    if (visited.has(start)) continue;
    visited.add(start);
    const stack = [{ id: start, next: 0 }];
    while (stack.length) {
      const frame = stack[stack.length - 1];
      const neighbors = outgoing.get(frame.id) || [];
      if (frame.next < neighbors.length) {
        const neighbor = neighbors[frame.next];
        frame.next += 1;
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          stack.push({ id: neighbor, next: 0 });
        }
      } else {
        finishOrder.push(frame.id);
        stack.pop();
      }
    }
  }

  const componentOf = new Map();
  const components = [];
  for (let i = finishOrder.length - 1; i >= 0; i -= 1) {
    const start = finishOrder[i];
    if (componentOf.has(start)) continue;
    const componentId = components.length;
    const component = [];
    const stack = [start];
    componentOf.set(start, componentId);
    while (stack.length) {
      const id = stack.pop();
      component.push(id);
      for (const neighbor of incoming.get(id) || []) {
        if (componentOf.has(neighbor)) continue;
        componentOf.set(neighbor, componentId);
        stack.push(neighbor);
      }
    }
    components.push(component);
  }
  return { componentOf, components };
}

function componentDepths(components, componentOf, edges) {
  const outgoing = components.map(() => new Set());
  const indegree = components.map(() => 0);
  for (const edge of edges) {
    const from = componentOf.get(edge.from);
    const to = componentOf.get(edge.to);
    if (from === to || outgoing[from].has(to)) continue;
    outgoing[from].add(to);
    indegree[to] += 1;
  }

  const depth = components.map(() => 0);
  const queue = [];
  indegree.forEach((count, component) => { if (count === 0) queue.push(component); });
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const component = queue[cursor];
    for (const next of outgoing[component]) {
      depth[next] = Math.max(depth[next], depth[component] + 1);
      indegree[next] -= 1;
      if (indegree[next] === 0) queue.push(next);
    }
  }
  return depth;
}

// SCC condensation + DAG longest path is O(V + E). Sorting within layers adds O(V log V).
export function layeredLayout(nodes, edges, options = {}) {
  const columnWidth = options.columnWidth || 300;
  const rowHeight = options.rowHeight || 118;
  const subcolumnWidth = options.subcolumnWidth || 250;
  const maxPerColumn = options.maxPerColumn || 10;
  if (!nodes.length) return {};

  const graph = adjacencyFor(nodes, edges);
  const { componentOf, components } = stronglyConnectedComponents(graph.ids, graph.outgoing, graph.incoming);
  const componentDepth = componentDepths(components, componentOf, graph.keptEdges);
  const layers = new Map();
  for (const node of nodes) {
    const depth = componentDepth[componentOf.get(node.id)] || 0;
    if (!layers.has(depth)) layers.set(depth, []);
    layers.get(depth).push(node);
  }

  const positions = {};
  let xCursor = 0;
  for (const depth of [...layers.keys()].sort((a, b) => a - b)) {
    const column = layers.get(depth).slice().sort((a, b) =>
      String(a.type).localeCompare(String(b.type)) || String(a.id).localeCompare(String(b.id)));
    const subcolumns = Math.max(1, Math.ceil(column.length / maxPerColumn));
    const rowsPerColumn = Math.ceil(column.length / subcolumns);
    column.forEach((node, index) => {
      const subcolumn = Math.floor(index / rowsPerColumn);
      const row = index % rowsPerColumn;
      const rowsHere = Math.min(rowsPerColumn, column.length - subcolumn * rowsPerColumn);
      positions[node.id] = {
        x: xCursor + subcolumn * subcolumnWidth,
        y: (row - (rowsHere - 1) / 2) * rowHeight,
      };
    });
    xCursor += (subcolumns - 1) * subcolumnWidth + columnWidth;
  }
  return positions;
}
