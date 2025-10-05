from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import RunnableConfig


async def thread_exists(saver: AsyncSqliteSaver, thread_id: str) -> bool:
    config = RunnableConfig({"configurable": {"thread_id": thread_id}})
    result = await saver.aget(config)
    return True if result else False
