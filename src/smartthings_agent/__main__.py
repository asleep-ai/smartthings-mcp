"""Run OpenAI-compatible server with SmartThings agent."""

import json
import logging
import os
import time

import litellm
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .handler import RESPONSE_ID_PREFIX, SmartThingsAgentError, SmartThingsLLM

# Configuration from environment
HOST = os.environ.get("SMARTTHINGS_AGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("SMARTTHINGS_AGENT_PORT", "8000"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create handler instance
handler = SmartThingsLLM()

# Register custom handler
litellm.custom_provider_map = [
    {"provider": "smartthings", "custom_handler": handler}
]

app = FastAPI(title="SmartThings Agent")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "smartthings/agent"
    messages: list[Message]
    stream: bool = False


async def stream_response(request: ChatRequest):
    """Generate SSE stream for OpenAI-compatible streaming."""
    logger.info("[server] starting SSE stream")

    try:
        async for chunk in handler.astreaming(
            model=request.model,
            messages=[m.model_dump() for m in request.messages],
        ):
            # GenericStreamingChunk is a TypedDict, access as dict
            text = chunk.get("text") or chunk.get("content") or ""
            is_finished = chunk.get("is_finished", False)

            if text:
                data = {
                    "id": RESPONSE_ID_PREFIX,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None,
                        }
                    ],
                }
                logger.debug(f"[server] SSE chunk: {text[:50]}...")
                yield f"data: {json.dumps(data)}\n\n"

            if is_finished:
                data = {
                    "id": RESPONSE_ID_PREFIX,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"
                logger.info("[server] SSE stream completed")
    except SmartThingsAgentError as e:
        logger.error(f"[server] agent error during streaming: {e}")
        error_data = {
            "error": {
                "message": str(e),
                "type": "agent_error",
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"
    except ValueError as e:
        logger.error(f"[server] validation error: {e}")
        error_data = {
            "error": {
                "message": str(e),
                "type": "invalid_request_error",
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    logger.info(f"[server] request - stream={request.stream}, messages={len(request.messages)}")

    if request.stream:
        return StreamingResponse(
            stream_response(request),
            media_type="text/event-stream",
        )

    try:
        response = await litellm.acompletion(
            model=request.model,
            messages=[m.model_dump() for m in request.messages],
        )
        logger.info("[server] non-streaming response completed")
        return response.model_dump()
    except SmartThingsAgentError as e:
        logger.error(f"[server] agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        logger.error(f"[server] validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    logger.info(f"[server] starting on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
