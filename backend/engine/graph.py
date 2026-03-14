# engine/graph.py
from langgraph.graph import StateGraph, END
from engine.state import SubtitleAnalysisState
from engine.nodes.subtitle_extractor import subtitle_extractor_node
from engine.nodes.chunk_splitter import chunk_splitter_node
from engine.nodes.chunk_summarizer import chunk_summarizer_node
from engine.nodes.final_summarizer import final_summarizer_node
from engine.nodes.insight_generator import insight_generator_node


def build_graph():
    graph = StateGraph(SubtitleAnalysisState)

    graph.add_node("subtitle_extractor", subtitle_extractor_node)
    graph.add_node("chunk_splitter", chunk_splitter_node)
    graph.add_node("chunk_summarizer", chunk_summarizer_node)
    graph.add_node("final_summarizer", final_summarizer_node)
    graph.add_node("insight_generator", insight_generator_node)

    graph.set_entry_point("subtitle_extractor")
    graph.add_edge("subtitle_extractor", "chunk_splitter")
    graph.add_edge("chunk_splitter", "chunk_summarizer")
    graph.add_edge("chunk_summarizer", "final_summarizer")
    graph.add_edge("final_summarizer", "insight_generator")
    graph.add_edge("insight_generator", END)

    return graph.compile()
