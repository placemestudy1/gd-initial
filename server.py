"""
server.py — FastAPI Token Server for GD Arena

Endpoints:
  POST /api/create-session   → Create room + user token + dispatch agents
  GET  /api/topics           → Get categorized GD topic library
  GET  /api/session/{room}   → Get session status
  GET  /                     → Serve frontend index.html
  GET  /static/*             → Serve static frontend assets

Run:
  python server.py
  → Starts at http://localhost:8000
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("=" * 50)
    logger.info("PlaceMe GD Arena Server Starting...")
    logger.info(f"LiveKit URL: {os.getenv('LIVEKIT_URL', 'NOT SET')}")
    logger.info(f"Groq API: {'✓ configured' if os.getenv('GROQ_API_KEY') else '✗ missing'}")
    logger.info(f"Google API: {'✓ configured' if os.getenv('GOOGLE_API_KEY') else '✗ missing'}")
    logger.info("=" * 50)
    yield
    # Shutdown (nothing to do)


app = FastAPI(title="PlaceMe GD Arena API", version="1.0.0", lifespan=lifespan)

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active sessions tracking
active_sessions: dict = {}


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    topic: str
    user_name: str = "You"
    duration: int = 600  # seconds


class CreateSessionResponse(BaseModel):
    room_name: str
    token: str
    ws_url: str
    topic: str
    duration: int
    session_id: str


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/create-session", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    """
    Creates a LiveKit room, generates a user JWT token,
    and dispatches all three AI agents into the room.
    """
    from livekit import api as lkapi_module

    lk_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")

    if not lk_key or not lk_secret:
        raise HTTPException(500, "LiveKit credentials not configured")

    room_name = f"gd-{uuid.uuid4().hex[:8]}"
    session_id = uuid.uuid4().hex[:12]

    session_config = {
        "topic": req.topic,
        "user_name": req.user_name,
        "duration": req.duration,
        "session_id": session_id,
    }

    initial_metadata = json.dumps({
        "session_config": session_config
    })

    try:
        async with lkapi_module.LiveKitAPI(lk_url, lk_key, lk_secret) as lk:
            # 1. Create the LiveKit room
            await lk.room.create_room(
                lkapi_module.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=300,
                    max_participants=10,
                    metadata=initial_metadata,
                )
            )
            logger.info(f"Room created: {room_name}")

            # 2. Generate user access token
            user_identity = req.user_name.lower().replace(" ", "_")
            token = lkapi_module.AccessToken(lk_key, lk_secret) \
                .with_identity(user_identity) \
                .with_name(req.user_name) \
                .with_grants(lkapi_module.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                ))
            token_str = token.to_jwt()

            # 3. Dispatch AI agents (fire-and-forget, don't block the response)
            asyncio.create_task(
                _dispatch_agents(lk_url, lk_key, lk_secret, room_name, req.topic, req.user_name, req.duration)
            )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(500, f"Failed to create session: {str(e)}")

    # Track session
    active_sessions[room_name] = {
        "session_id": session_id,
        "topic": req.topic,
        "user_name": req.user_name,
        "duration": req.duration,
        "started": True,
    }

    return CreateSessionResponse(
        room_name=room_name,
        token=token_str,
        ws_url=os.getenv("LIVEKIT_URL", ""),
        topic=req.topic,
        duration=req.duration,
        session_id=session_id,
    )


async def _dispatch_agents(lk_url, lk_key, lk_secret, room_name, topic, user_name, duration):
    """Dispatch all three agents to the room (runs in background task)."""
    import asyncio
    from livekit import api as lkapi_module

    await asyncio.sleep(1.0)  # Small delay so room is fully ready

    agent_configs = [
        ("moderator-agent", "moderator"),
        ("aarav-agent",     "debater_aarav"),
        ("priya-agent",     "debater_priya"),
    ]

    async with lkapi_module.LiveKitAPI(lk_url, lk_key, lk_secret) as lk:
        for agent_name, role in agent_configs:
            try:
                dispatch = await lk.agent_dispatch.create_dispatch(
                    lkapi_module.CreateAgentDispatchRequest(
                        agent_name=agent_name,
                        room=room_name,
                        metadata=json.dumps({
                            "role": role,
                            "topic": topic,
                            "user_name": user_name,
                            "duration": duration,
                        })
                    )
                )
                logger.info(f"✓ Dispatched {agent_name}")
            except Exception as e:
                logger.warning(f"✗ Could not dispatch {agent_name}: {e}")
            await asyncio.sleep(0.5)


@app.get("/api/topics")
async def get_topics():
    """Returns the curated GD topic library."""
    from agents.prompts import GD_TOPICS
    return {"topics": GD_TOPICS}


@app.get("/api/session/{room_name}")
async def get_session_status(room_name: str):
    """Returns current session status."""
    if room_name not in active_sessions:
        raise HTTPException(404, "Session not found")
    return active_sessions[room_name]


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "PlaceMe GD Arena"}


# ─────────────────────────────────────────────────────────────────────────────
# Serve Frontend
# ─────────────────────────────────────────────────────────────────────────────

frontend_dir = Path(__file__).parent / "frontend"

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return HTMLResponse("<h1>GD Arena Frontend not found</h1>", status_code=404)

    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(frontend_dir / "app.js"))

    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(str(frontend_dir / "styles.css"))
else:
    @app.get("/")
    async def no_frontend():
        return HTMLResponse(
            "<h1>PlaceMe GD Arena API</h1>"
            "<p>Frontend not built. See /docs for API documentation.</p>",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
