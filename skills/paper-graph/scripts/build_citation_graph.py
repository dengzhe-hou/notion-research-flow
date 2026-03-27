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


def main():
    parser = argparse.ArgumentParser(description="Build citation graph for a paper")
    parser.add_argument("identifier", help="arXiv ID, DOI, S2 ID, or paper title")
    parser.add_argument("--api-key", default=None, help="Semantic Scholar API key")
    parser.add_argument("--max-refs", type=int, default=10, help="Max references to fetch")
    parser.add_argument("--max-cites", type=int, default=10, help="Max citations to fetch")
    parser.add_argument("--depth", type=int, default=1, choices=[1, 2], help="Graph depth")
    parser.add_argument("--format", choices=["json", "mermaid"], default="json", help="Output format")

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
    else:
        print(json.dumps(graph, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
