# tests/test_new_graph.py
from engine.graph import build_graph


def test_graph_builds():
    """그래프가 정상적으로 빌드되는지 테스트"""
    graph = build_graph()
    assert graph is not None


def test_graph_has_correct_nodes():
    """그래프에 올바른 노드가 있는지 테스트"""
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {
        "__start__",
        "__end__",
        "subtitle_extractor",
        "chunk_splitter",
        "chunk_summarizer",
        "final_summarizer",
        "insight_generator",
    }
    assert expected.issubset(node_names)
