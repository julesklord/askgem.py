import logging
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..agent.chat import ChatAgent

_logger = logging.getLogger("mentask.api")
app = FastAPI(title="MentAsk Agent API Server", version="1.0.0")


class QueryRequest(BaseModel):
    message: str


@app.post("/query")
async def handle_query(request: QueryRequest) -> dict[str, Any]:
    """
    Synchronous endpoint that collects events and returns the final accumulated text.
    """
    agent = ChatAgent()
    events = []
    text_chunks = []
    try:
        async for event in agent.stream_response(request.message):
            events.append(event.model_dump(mode="json"))
            if event.event_type == "text_chunk":
                text_chunks.append(event.content)
        return {
            "reply": "".join(text_chunks),
            "events": events
        }
    finally:
        await agent.close()


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint that streams structured agent events (StatusEvent, ThoughtEvent,
    ToolCallEvent, ToolResultEvent) to the client in real-time.
    """
    await websocket.accept()
    agent = ChatAgent()
    try:
        while True:
            data = await websocket.receive_json()
            user_msg = data.get("message", "")
            if not user_msg:
                continue

            async for event in agent.stream_response(user_msg):
                await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        _logger.info("WebSocket client disconnected.")
    except Exception as e:
        _logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"event_type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        await agent.close()
