"""Graph export helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from extractory.export import export_csv, export_jsonl, to_jsonable
from extractory.graph.models import GraphEdge, GraphNode, GraphResult


def graph_to_node_link_json(graph: GraphResult) -> str:
    """Return graph as node-link JSON text."""
    return json.dumps(to_jsonable(graph), ensure_ascii=False, sort_keys=True)


def export_nodes_jsonl(nodes: Iterable[GraphNode], path_or_file: str | Path | TextIO) -> None:
    """Export graph nodes as JSON Lines."""
    export_jsonl(nodes, path_or_file)


def export_edges_jsonl(edges: Iterable[GraphEdge], path_or_file: str | Path | TextIO) -> None:
    """Export graph edges as JSON Lines."""
    export_jsonl(edges, path_or_file)


def export_nodes_csv(nodes: Iterable[GraphNode], path_or_file: str | Path | TextIO) -> None:
    """Export graph nodes as CSV."""
    export_csv(nodes, path_or_file)


def export_edges_csv(edges: Iterable[GraphEdge], path_or_file: str | Path | TextIO) -> None:
    """Export graph edges as CSV."""
    export_csv(edges, path_or_file)


def graph_to_mermaid(graph: GraphResult) -> str:
    """Return a Mermaid graph description."""
    lines = ["graph TD"]
    for node in graph.nodes:
        label = (node.label or node.id).replace('"', "'")
        lines.append(f'  {node.id.replace(":", "_").replace("-", "_")}["{label}"]')
    for edge in graph.edges:
        source = edge.source_id.replace(":", "_").replace("-", "_")
        target = edge.target_id.replace(":", "_").replace("-", "_")
        label = f"|{edge.label or edge.kind}|" if edge.label or edge.kind else ""
        lines.append(f"  {source} -->{label} {target}")
    return "\n".join(lines)


def graph_to_dot(graph: GraphResult) -> str:
    """Return a DOT graph description."""
    lines = ["digraph extractory {"]
    for node in graph.nodes:
        label = (node.label or node.id).replace('"', "'")
        lines.append(f'  "{node.id}" [label="{label}"];')
    for edge in graph.edges:
        label = (edge.label or edge.kind).replace('"', "'")
        lines.append(f'  "{edge.source_id}" -> "{edge.target_id}" [label="{label}"];')
    lines.append("}")
    return "\n".join(lines)
