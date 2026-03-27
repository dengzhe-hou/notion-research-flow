#!/usr/bin/env python3
"""Build a citation graph for a paper using Semantic Scholar API.

Given a paper identifier (arXiv ID, DOI, S2 ID, or title),
fetches references and citations, then outputs a JSON structure
suitable for rendering as a Mermaid diagram.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request


API_BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,citationCount,year,externalIds,url,authors"
DELAY = 1.0  # seconds between API calls


def _api_get(url, api_key=None, retries=3):
    """Make a GET request to Semantic Scholar API with retry on 429."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = 5 * (attempt + 1)  # exponential: 5, 10, 15s
                print(f"Rate limited, waiting {wait}s... (attempt {attempt+1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            elif e.code == 404:
                return None
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(2)
                continue
            return None
    return None


def resolve_paper(identifier, api_key=None):
    """Resolve a paper identifier to Semantic Scholar paper data."""
    # Try as arXiv ID
    if identifier.replace(".", "").replace("/", "").isalnum():
        url = f"{API_BASE}/paper/ARXIV:{identifier}?fields={FIELDS}"
        result = _api_get(url, api_key)
        if result:
            return result

    # Try as DOI
    if "/" in identifier:
        url = f"{API_BASE}/paper/DOI:{identifier}?fields={FIELDS}"
        result = _api_get(url, api_key)
        if result:
            return result

    # Try as S2 ID or CorpusId (only if it looks like an ID — no spaces)
    if " " not in identifier:
        url = f"{API_BASE}/paper/{identifier}?fields={FIELDS}"
        result = _api_get(url, api_key)
        if result:
            return result

    # Fallback: search by title
    query = urllib.parse.quote(identifier)
    url = f"{API_BASE}/paper/search?query={query}&limit=1&fields={FIELDS}"
    result = _api_get(url, api_key)
    if result and result.get("data"):
        return result["data"][0]

    return None


def fetch_references(paper_id, api_key=None, limit=10):
    """Fetch papers that this paper cites (references)."""
    fields = f"title,citationCount,year,externalIds,url"
    url = f"{API_BASE}/paper/{paper_id}/references?fields={fields}&limit={limit}"
    time.sleep(DELAY)
    result = _api_get(url, api_key)
    if not result or "data" not in result:
        return []
    papers = []
    for item in result["data"]:
        cited = item.get("citedPaper")
        if cited and cited.get("title"):
            papers.append(cited)
    return papers


def fetch_citations(paper_id, api_key=None, limit=10):
    """Fetch papers that cite this paper."""
    fields = f"title,citationCount,year,externalIds,url"
    url = f"{API_BASE}/paper/{paper_id}/citations?fields={fields}&limit={limit}"
    time.sleep(DELAY)
    result = _api_get(url, api_key)
    if not result or "data" not in result:
        return []
    papers = []
    for item in result["data"]:
        citing = item.get("citingPaper")
        if citing and citing.get("title"):
            papers.append(citing)
    return papers


def _short_title(title, max_len=40):
    """Truncate title for display in graph nodes."""
    if len(title) <= max_len:
        return title
    return title[:max_len - 3] + "..."


def _sanitize_mermaid(text):
    """Escape characters that break Mermaid syntax."""
    return text.replace('"', "'").replace("\n", " ").replace("[", "(").replace("]", ")")


def _node_id(paper):
    """Generate a stable node ID for a paper."""
    s2_id = paper.get("paperId", "")
    if s2_id:
        return f"p_{s2_id[:12]}"
    # fallback to hash of title
    return f"p_{abs(hash(paper.get('title', ''))) % 10**8}"


def build_graph(identifier, api_key=None, max_refs=10, max_cites=10, depth=1):
    """Build citation graph and return structured data."""
    # Resolve the seed paper
    seed = resolve_paper(identifier, api_key)
    if not seed:
        return {"error": f"Could not find paper: {identifier}"}

    seed_id = seed["paperId"]
    nodes = {}
    edges = []

    # Add seed node
    nodes[seed_id] = {
        "id": seed_id,
        "title": seed.get("title", "Unknown"),
        "year": seed.get("year"),
        "citations": seed.get("citationCount", 0),
        "arxiv_id": (seed.get("externalIds") or {}).get("ArXiv"),
        "url": seed.get("url", ""),
        "role": "seed",
    }

    # Fetch references (papers the seed cites)
    refs = fetch_references(seed_id, api_key, limit=max_refs)
    for paper in refs:
        pid = paper.get("paperId", "")
        if not pid:
            continue
        nodes[pid] = {
            "id": pid,
            "title": paper.get("title", "Unknown"),
            "year": paper.get("year"),
            "citations": paper.get("citationCount", 0),
            "arxiv_id": (paper.get("externalIds") or {}).get("ArXiv"),
            "url": paper.get("url", ""),
            "role": "reference",
        }
        edges.append({"from": seed_id, "to": pid, "type": "cites"})

    # Fetch citations (papers that cite the seed)
    cites = fetch_citations(seed_id, api_key, limit=max_cites)
    for paper in cites:
        pid = paper.get("paperId", "")
        if not pid:
            continue
        if pid not in nodes:
            nodes[pid] = {
                "id": pid,
                "title": paper.get("title", "Unknown"),
                "year": paper.get("year"),
                "citations": paper.get("citationCount", 0),
                "arxiv_id": (paper.get("externalIds") or {}).get("ArXiv"),
                "url": paper.get("url", ""),
                "role": "citation",
            }
        edges.append({"from": pid, "to": seed_id, "type": "cited_by"})

    # Depth 2: fetch references of top-cited references (optional)
    if depth >= 2:
        top_refs = sorted(refs, key=lambda p: p.get("citationCount", 0), reverse=True)[:3]
        for ref in top_refs:
            ref_id = ref.get("paperId", "")
            if not ref_id:
                continue
            sub_refs = fetch_references(ref_id, api_key, limit=5)
            for paper in sub_refs:
                pid = paper.get("paperId", "")
                if not pid:
                    continue
                if pid not in nodes:
                    nodes[pid] = {
                        "id": pid,
                        "title": paper.get("title", "Unknown"),
                        "year": paper.get("year"),
                        "citations": paper.get("citationCount", 0),
                        "arxiv_id": (paper.get("externalIds") or {}).get("ArXiv"),
                        "url": paper.get("url", ""),
                        "role": "extended",
                    }
                edges.append({"from": ref_id, "to": pid, "type": "cites"})

    return {
        "seed": seed_id,
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "references": len(refs),
            "citations": len(cites),
        },
    }


def graph_to_mermaid(graph_data):
    """Convert graph data to Mermaid flowchart string."""
    if "error" in graph_data:
        return f"graph LR\n    err[{graph_data['error']}]"

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    seed_id = graph_data["seed"]

    lines = ["graph LR"]

    # Define node styles
    lines.append("")
    lines.append("    %% Node definitions")

    for nid, node in nodes.items():
        safe_id = _node_id(node)
        title = _sanitize_mermaid(_short_title(node["title"]))
        year = node.get("year") or "?"
        cites = node.get("citations", 0)
        label = f"{title}<br/>({year}, {cites} cites)"

        if node["role"] == "seed":
            lines.append(f'    {safe_id}["{label}"]')
        elif node["role"] == "reference":
            lines.append(f'    {safe_id}("{label}")')
        elif node["role"] == "citation":
            lines.append(f'    {safe_id}(["{label}"])')
        else:
            lines.append(f'    {safe_id}("{label}")')

    lines.append("")
    lines.append("    %% Edges")

    # Build ID mapping
    id_map = {nid: _node_id(nodes[nid]) for nid in nodes}

    for edge in edges:
        from_id = id_map.get(edge["from"])
        to_id = id_map.get(edge["to"])
        if from_id and to_id:
            if edge["type"] == "cites":
                lines.append(f"    {from_id} --> {to_id}")
            else:
                lines.append(f"    {from_id} -.-> {to_id}")

    # Style the seed node
    seed_safe = id_map.get(seed_id)
    if seed_safe:
        lines.append("")
        lines.append(f"    style {seed_safe} fill:#ff6b6b,stroke:#c92a2a,stroke-width:3px,color:#fff")

    # Style by role
    ref_ids = [id_map[nid] for nid, n in nodes.items() if n["role"] == "reference" and nid in id_map]
    cite_ids = [id_map[nid] for nid, n in nodes.items() if n["role"] == "citation" and nid in id_map]

    for rid in ref_ids:
        lines.append(f"    style {rid} fill:#4dabf7,stroke:#1971c2,color:#fff")
    for cid in cite_ids:
        lines.append(f"    style {cid} fill:#69db7c,stroke:#2b8a3e,color:#fff")

    return "\n".join(lines)


def graph_to_html(graph_data):
    """Convert graph data to an interactive HTML file using Mermaid.js."""
    mermaid_code = graph_to_mermaid(graph_data)
    seed_node = graph_data.get("nodes", {}).get(graph_data.get("seed", ""), {})
    title = seed_node.get("title", "Citation Graph")
    stats = graph_data.get("stats", {})

    # Build clickable link map
    nodes = graph_data.get("nodes", {})
    link_script_parts = []
    for nid, node in nodes.items():
        safe_id = _node_id(node)
        url = node.get("url", "")
        if url:
            link_script_parts.append(
                f'document.querySelectorAll("[id*=\\"{safe_id}\\"]").forEach(el => '
                f'el.style.cursor = "pointer");'
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Citation Graph — {title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #fafafa; }}
  h1 {{ font-size: 1.4em; margin-bottom: 4px; }}
  .subtitle {{ color: #666; margin-bottom: 16px; font-size: 0.9em; }}
  .legend {{ display: flex; gap: 20px; margin-bottom: 16px; font-size: 0.85em; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  .dot-seed {{ background: #ff6b6b; }}
  .dot-ref {{ background: #4dabf7; }}
  .dot-cite {{ background: #69db7c; }}
  .dot-ext {{ background: #da77f2; }}
  #graph {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; overflow: auto; }}
  .stats {{ margin-top: 12px; font-size: 0.85em; color: #888; }}
</style>
</head>
<body>
<h1>Citation Graph</h1>
<p class="subtitle">{title}</p>
<div class="legend">
  <span class="legend-item"><span class="dot dot-seed"></span> Seed paper</span>
  <span class="legend-item"><span class="dot dot-ref"></span> References ({stats.get('references', 0)})</span>
  <span class="legend-item"><span class="dot dot-cite"></span> Citations ({stats.get('citations', 0)})</span>
</div>
<div id="graph">
<pre class="mermaid">
{mermaid_code}
</pre>
</div>
<p class="stats">{stats.get('total_nodes', 0)} nodes, {stats.get('total_edges', 0)} edges &mdash; Generated by notion-research-flow /paper-graph</p>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Build citation graph for a paper")
    parser.add_argument("identifier", help="arXiv ID, DOI, S2 ID, or paper title")
    parser.add_argument("--api-key", default=None, help="Semantic Scholar API key")
    parser.add_argument("--max-refs", type=int, default=10, help="Max references to fetch")
    parser.add_argument("--max-cites", type=int, default=10, help="Max citations to fetch")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2], help="Graph depth")
    parser.add_argument("--format", choices=["json", "mermaid", "html"], default="json", help="Output format")
    parser.add_argument("--output", "-o", default=None, help="Output file path (for html format)")

    args = parser.parse_args()

    graph = build_graph(
        args.identifier,
        api_key=args.api_key,
        max_refs=args.max_refs,
        max_cites=args.max_cites,
        depth=args.depth,
    )

    if args.format == "mermaid":
        print(graph_to_mermaid(graph))
    elif args.format == "html":
        html = graph_to_html(graph)
        if args.output:
            out_path = args.output
        else:
            import re
            seed_title = graph.get("nodes", {}).get(graph.get("seed", ""), {}).get("title", "graph")
            safe_name = re.sub(r'[^\w\s-]', '', seed_title)[:50].strip().replace(' ', '_')
            out_path = f"citation_graph_{safe_name}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Graph saved to: {out_path}")
    else:
        print(json.dumps(graph, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
