# engine/graph.py
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph, END
from engine.state import WebinarState
from engine.nodes.stt_node import stt_node
from engine.nodes.fast_translator import fast_translator
from engine.nodes.context_refiner import context_refiner
from engine.nodes.insight_extractor import insight_extractor


def both_tracks(state: WebinarState):
    """Run fast_translator and context_refiner in PARALLEL for speed."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        fast_future = pool.submit(fast_translator, state)
        refiner_future = pool.submit(context_refiner, state)
        result = fast_future.result()
        refiner_result = refiner_future.result()

    combined_events = result.get("ui_events", []) + refiner_result.get("ui_events", [])
    return {**refiner_result, "fast_translation": result["fast_translation"],
            "ui_events": combined_events}


def route_after_stt(state: WebinarState) -> str:
    if state.get("is_sentence_end"):
        return "both_tracks"
    return "fast_translator"


def route_after_refiner(state: WebinarState) -> str:
    refined = state.get("refined_sentences", [])
    if len(refined) > 0 and len(refined) % 5 == 0:
        return "insight_extractor"
    return END


def build_graph():
    graph = StateGraph(WebinarState)

    graph.add_node("stt_node", stt_node)
    graph.add_node("fast_translator", fast_translator)
    graph.add_node("both_tracks", both_tracks)
    graph.add_node("insight_extractor", insight_extractor)

    graph.set_entry_point("stt_node")
    graph.add_conditional_edges("stt_node", route_after_stt, {
        "both_tracks": "both_tracks",
        "fast_translator": "fast_translator",
    })
    graph.add_edge("fast_translator", END)
    graph.add_conditional_edges("both_tracks", route_after_refiner, {
        "insight_extractor": "insight_extractor",
        END: END,
    })
    graph.add_edge("insight_extractor", END)

    return graph.compile()
