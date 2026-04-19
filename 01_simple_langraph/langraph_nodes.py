from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
import getpass
import os
from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

memory = MemorySaver()

# Simple state — plain key-value
class SimpleState(TypedDict):
    topic: str
    draft: str
    score: int
    approved: bool

# Message-aware state (for conversational agents)
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # add_messages is a REDUCER — it appends new messages instead of overriding
    context: str
    iteration: int

api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    api_key=api_key,
    model="qwen/qwen3-32b",
    temperature=0,
    max_tokens=None,
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
)

# Node 1 — Simple LLM call
def generate_draft(state: SimpleState) -> dict:
    """Writes a first draft on the given topic."""
    response = llm.invoke(f"Write a short paragraph about: {state['topic']}")
    return {"draft": response.content, "iteration": 1}

# Node 2 — Scoring agent
def score_draft(state: SimpleState) -> dict:
    """Scores the draft quality from 1–10."""
    prompt = f"""
    Rate this paragraph from 1–10 for clarity. Respond with ONLY a number.
    Paragraph: {state['draft']}
    """
    score = int(llm.invoke(prompt).content.strip())
    return {"score": score}

# Node 3 — Revision agent
def revise_draft(state: SimpleState) -> dict:
    """Improves a low-scoring draft."""
    response = llm.invoke(
        f"Improve this paragraph for clarity:\n{state['draft']}"
    )
    return {"draft": response.content}

def quality_gate(state: SimpleState) -> str:
    """Route based on quality score."""
    if state["score"] >= 7:
        return "approved"
    elif state["iteration"] >= 3:
        return "give_up"
    else:
        return "needs_work"


builder = StateGraph(SimpleState)

builder.add_node("generate", generate_draft)
builder.add_node("score", score_draft)
builder.add_node("revise", revise_draft)

builder.add_edge(START, "generate")
builder.add_edge("generate", "score")
builder.add_edge("revise", "score")


builder.add_conditional_edges(
    "score",
    quality_gate,
    {
        "approved":   END,
        "give_up":    END,
        "needs_work": "revise",
    }
)
graph = builder.compile(checkpointer=memory)

# Display graph
with open("graph.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())

# Run
result = graph.invoke({"topic": "quantum computing", "draft": "", "score": 0, "approved": False})

print("# Output")
print(result["draft"])