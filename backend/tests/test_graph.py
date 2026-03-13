# tests/test_graph.py
from engine.graph import build_graph, route_after_stt, route_after_refiner
from langgraph.graph import END


def test_graph_builds_without_error():
    graph = build_graph()
    assert graph is not None


def test_route_after_stt_incomplete_sentence():
    state = {"is_sentence_end": False}
    result = route_after_stt(state)
    assert result == "fast_translator"


def test_route_after_stt_complete_sentence():
    state = {"is_sentence_end": True}
    result = route_after_stt(state)
    assert result == "both_tracks"


def test_route_after_refiner_with_summary():
    state = {"refined_sentences": ["a", "b", "c", "d", "e"]}
    result = route_after_refiner(state)
    assert result == "insight_extractor"


def test_route_after_refiner_no_summary():
    state = {"refined_sentences": ["a", "b", "c"]}
    result = route_after_refiner(state)
    assert result == END
