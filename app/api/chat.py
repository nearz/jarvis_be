from uuid import uuid4

from fastapi import APIRouter, Depends

from langchain_core.messages import HumanMessage

from .dependencies import get_app_graph
from ..models.request_models import ChatRequest

# TODO: Move app logic to controllers

router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest, graph=Depends(get_app_graph)):
    thread_id = str(uuid4())
    result = await graph.ainvoke(
        {"messages": [HumanMessage(req.message)]},
        config={"configurable": {"thread_id": thread_id}},
        context={"llm": req.llm},
    )
    return {"ai_message": result["messages"][-1].content, "thread_id": thread_id}


@router.post("/chat/{thread_id}")
async def chat_thread(thread_id: str, req: ChatRequest, graph=Depends(get_app_graph)):
    print("Chat Thread EP")
    result = await graph.ainvoke(
        {"messages": [HumanMessage(req.message)]},
        config={"configurable": {"thread_id": thread_id}},
        context={"llm": req.llm},
    )
    return {"ai_message": result["messages"][-1].content}
