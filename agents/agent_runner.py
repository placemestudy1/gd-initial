"""
agents/agent_runner.py — Master Agent Dispatch Orchestrator

This is the MAIN entry point run as a single process.
It starts THREE separate agent workers (Moderator, Aarav, Priya)
and dispatches them all into the same LiveKit room.

Architecture:
  - Each agent is a separate WorkerOptions / AgentSession
  - All three join the same room simultaneously
  - They hear each other and the user through LiveKit's room audio
  - Turn-taking is coordinated via response delays + VAD
"""

import asyncio
import json
import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("agent_runner")


async def dispatch_agents_to_room(room_name: str, topic: str, user_name: str, duration: int = 600):
    """
    Dispatch all three AI agents to join the specified room.
    Uses LiveKit's Explicit Agent Dispatch API.
    """
    from livekit import api

    lk_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")

    logger.info(f"Dispatching agents to room: {room_name}")

    async with api.LiveKitAPI(lk_url, lk_key, lk_secret) as lkapi:
        # Dispatch Moderator
        try:
            dispatch1 = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="moderator-agent",
                    room=room_name,
                    metadata=json.dumps({
                        "role": "moderator",
                        "topic": topic,
                        "user_name": user_name,
                        "duration": duration
                    })
                )
            )
            logger.info(f"✓ Moderator dispatched: {dispatch1.agent_dispatch.id}")
        except Exception as e:
            logger.error(f"✗ Failed to dispatch Moderator: {e}")

        await asyncio.sleep(0.5)  # Small stagger to avoid race conditions

        # Dispatch Aarav
        try:
            dispatch2 = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="aarav-agent",
                    room=room_name,
                    metadata=json.dumps({
                        "role": "debater",
                        "persona": "aarav",
                        "topic": topic,
                        "user_name": user_name
                    })
                )
            )
            logger.info(f"✓ Aarav dispatched: {dispatch2.agent_dispatch.id}")
        except Exception as e:
            logger.error(f"✗ Failed to dispatch Aarav: {e}")

        await asyncio.sleep(0.5)

        # Dispatch Priya
        try:
            dispatch3 = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="priya-agent",
                    room=room_name,
                    metadata=json.dumps({
                        "role": "debater",
                        "persona": "priya",
                        "topic": topic,
                        "user_name": user_name
                    })
                )
            )
            logger.info(f"✓ Priya dispatched: {dispatch3.agent_dispatch.id}")
        except Exception as e:
            logger.error(f"✗ Failed to dispatch Priya: {e}")

    logger.info(f"All agents dispatched to room: {room_name}")


async def create_gd_room(topic: str, user_name: str, duration: int = 600) -> dict:
    """
    Create a LiveKit room and configure it with session metadata.
    Returns room info including name and token for the user.
    """
    from livekit import api
    import uuid

    lk_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")

    room_name = f"gd-arena-{uuid.uuid4().hex[:8]}"

    session_config = {
        "topic": topic,
        "user_name": user_name,
        "duration": duration,
        "started_at": None,
    }

    initial_metadata = json.dumps({
        "session_config": session_config,
    })

    async with api.LiveKitAPI(lk_url, lk_key, lk_secret) as lkapi:
        # Create room
        room_info = await lkapi.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,   # 5 min before auto-cleanup if empty
                max_participants=10,
                metadata=initial_metadata,
            )
        )
        logger.info(f"Room created: {room_name}")

        # Generate user access token
        user_token = api.AccessToken(lk_key, lk_secret) \
            .with_identity(user_name.lower().replace(" ", "_")) \
            .with_name(user_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            ))

        token_str = user_token.to_jwt()

    return {
        "room_name": room_name,
        "token": token_str,
        "ws_url": os.getenv("LIVEKIT_URL"),
        "topic": topic,
        "duration": duration,
    }


if __name__ == "__main__":
    # CLI mode for testing
    import argparse

    parser = argparse.ArgumentParser(description="GD Arena Agent Runner")
    parser.add_argument("--room", type=str, help="Room name to dispatch agents to")
    parser.add_argument("--topic", type=str,
                        default="Is AI a threat to jobs or creator of opportunities?")
    parser.add_argument("--user", type=str, default="Student")
    parser.add_argument("--duration", type=int, default=600)
    args = parser.parse_args()

    if args.room:
        asyncio.run(dispatch_agents_to_room(
            args.room, args.topic, args.user, args.duration
        ))
    else:
        # Create room and dispatch
        async def main():
            result = await create_gd_room(args.topic, args.user, args.duration)
            print(f"\n{'='*50}")
            print(f"Room created: {result['room_name']}")
            print(f"Token: {result['token'][:50]}...")
            print(f"{'='*50}\n")

            await dispatch_agents_to_room(
                result["room_name"],
                args.topic,
                args.user,
                args.duration,
            )

        asyncio.run(main())
