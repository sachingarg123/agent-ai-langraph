from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq
from langgraph.graph import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import os

load_dotenv()

class EmailState(TypedDict):
    instruction: str
    # The LLM-generated draft
    draft_subject: str
    draft_body:    str
    decision: str
    edited_body: str
    messages: Annotated[list[BaseMessage], add_messages] # Remember our reducer?

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

    # Node 1: draft the email
def draft_email(state: EmailState) -> dict:
    """LLM writes a subject + body from the user's instruction."""
    system = SystemMessage(content="""
    You are an expert email writer. Given an instruction, write a professional email.
    Respond in this exact format:
    SUBJECT: <subject line>
    BODY:
    <email body>
    """)
    user = HumanMessage(content=f"Instruction: {state['instruction']}")
    response = llm.invoke([system, user])

    # Parse the structured response
    lines = response.content.strip().split("\n")
    subject = ""
    body_lines = []
    in_body = False

    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)

    return {
        "draft_subject": subject,
        "draft_body":    "\n".join(body_lines).strip(),
        "messages":      [user, AIMessage(content=response.content)],
    }


# Node 2: get human review: this is where our graph will pause
def human_review(state: EmailState) -> dict:
    """
    Pauses the graph and surfaces the draft to the human.
    The human can respond with:
      - {"decision": "approve"}
      - {"decision": "edit", "edited_body": "...new body text..."}
      - {"decision": "discard"}
    """
    human_input = interrupt({
        "draft_subject": state["draft_subject"],
        "draft_body":    state["draft_body"],
        "prompt":        "Review this draft. Reply with approve / edit / discard.",
    })

    # human_input is whatever value was passed to Command(resume=...)
    decision    = human_input.get("decision", "discard")
    edited_body = human_input.get("edited_body", "")

    return {"decision": decision, "edited_body": edited_body}


# Node 3: sending email
def send_email(state: EmailState) -> dict:
    """Sends the approved (or edited) email."""
    final_body = state["edited_body"] if state["edited_body"] else state["draft_body"]
    print(f"\n📧 EMAIL SENT")
    print(f"   Subject : {state['draft_subject']}")
    print(f"   Body    :\n{final_body}")
    return {"messages": [AIMessage(content=f"Email sent: {state['draft_subject']}")]}


# Node 4: Discard email
def discard_email(state: EmailState) -> dict:
    """Human chose not to send the email."""
    print("\n🗑️  Email discarded by user.")
    return {"messages": [AIMessage(content="Email discarded.")]}


def route_after_review(state: EmailState) -> Literal["send_email", "discard_email"]:
    """Branch based on the human's decision."""
    if state["decision"] == "approve":
        return "send_email"
    elif state["decision"] == "edit":
        return "send_email"
    else:
        return "discard_email"
    
    # Build
builder = StateGraph(EmailState)
builder.add_node("draft_email",   draft_email)
builder.add_node("human_review",  human_review)
builder.add_node("send_email",    send_email)
builder.add_node("discard_email", discard_email)

builder.add_edge(START,          "draft_email")
builder.add_edge("draft_email",  "human_review")
builder.add_conditional_edges(
    "human_review",
    route_after_review,
    {"send_email": "send_email", "discard_email": "discard_email"},
)
builder.add_edge("send_email",    END)
builder.add_edge("discard_email", END)

# ⚠️  MemorySaver is REQUIRED — HITL needs a place to save frozen state
memory  = MemorySaver()
graph   = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "email-session-001"}}

initial_state = {
    "instruction":    "Write an email to the team announcing our product launch next Friday.",
    "draft_subject":  "",
    "draft_body":     "",
    "decision":       "",
    "edited_body":    "",
    "messages":       [],
}

print("🤖 Drafting email...\n")


graph.invoke(initial_state, config=config)
snapshot = graph.get_state(config) # get current state of the graph
pending  = snapshot.next
review_payload = snapshot.values
print(f"\n⏸️  Graph paused at: {pending}")
print(f"\n{'='*50}")
print(f"  SUBJECT : {review_payload['draft_subject']}")
print(f"  BODY    :\n{review_payload['draft_body']}")
print(f"{'='*50}")

#Scenario 1 :  approve to send emaiil as is
#graph.invoke(
#    Command(resume={"decision": "approve"}),
#    config=config,
#)

# Scenario 2 : Edit the body then approve
#graph.invoke(
 #   Command(resume={
  #      "decision":    "edit",
   #     "edited_body": "Hi team,\nBig news — we're launching next Friday at 10am IST!\nStay tuned.\n— The Team",
    #}),
    #config=config,
#)

# Scenario 3 : Discard

graph.invoke(
     Command(resume={"decision": "discard"}),
     config=config,
 )