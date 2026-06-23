from extractory.graph import GraphEdge, GraphNode, GraphResult


def test_graph_result_deduplicates_nodes_and_keeps_distinct_edges() -> None:
    graph = GraphResult()

    assert graph.add_node(GraphNode(id="jira:ABC-1", kind="jira_issue", source="jira"))
    assert not graph.add_node(GraphNode(id="jira:ABC-1", kind="jira_issue", source="jira"))
    assert graph.add_edge(
        GraphEdge(
            id="edge-1",
            source_id="jira:ABC-1",
            target_id="jira:ABC-2",
            kind="blocks",
            source_system="jira",
        )
    )

    assert graph.stats.visited_nodes == 1
    assert graph.stats.visited_edges == 1
