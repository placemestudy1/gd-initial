# Phase 1

Welcome to the **PlaceMe GD Arena**, an immersive and interactive web application designed to help users prepare for placement group discussions. The platform simulates a real-world Group Discussion (GD) environment using AI agents powered by LiveKit and Large Language Models.

## The Vision

**The Core Problem**: Engineering students spend years mastering coursework, but are often blindsided when placement season arrives due to a lack of practical rehearsal. Reading about a Group Discussion is fundamentally different from participating in one. Students need a way to practice speaking, thinking on their feet, and handling pressure.

**The Solution**: PlaceMe is a digital practice arena designed for college students preparing for placements. It provides a safe, on-demand environment to rehearse the placement drive and receive instant, easy-to-understand feedback.

## The Group Discussion (GD) Arena

The GD Arena is a core module of PlaceMe—a simulated environment where students can practice making their voices heard in a group setting. 

### Key Practice Modes

- **AI Voice Practice**: Select a topic and a timer (e.g., 5 or 10 minutes). You are placed in a virtual room with computer-generated participants. You must speak out loud, make your points, and interact naturally.
- **Multiplayer Practice**: Invite classmates to a private room where PlaceMe provides the topic and timer for collaborative rehearsal.
- **Feedback**: After the session, the system provides a simple report assessing if you spoke clearly, stayed on topic, and let others speak.

### The AI Participants

1. **Moderator (Kavya)**: Guides the discussion, introduces the topic, ensures smooth transitions, tracks time, and provides a concluding summary.
2. **Aarav Debater**: An AI debater with a distinct personality, providing strong arguments and counter-points.
3. **Priya Debater**: Another AI debater with unique perspectives, balancing the discussion dynamics.

## Architecture & Core Mechanics

### Shared Context Memory (`shared_context.py`)
All AI agents share a single context store backed by **LiveKit Room Metadata**. This provides several critical advantages:
- **Token Optimization (70%+ Reduction)**: Instead of passing the entire raw transcript to every agent on every turn, the context manager auto-summarizes older utterances into "key arguments". Agents only receive the topic, current phase, key arguments summary, and the last 3 raw utterances.
- **Phase Management**: The system automatically advances through discussion phases (`opening` → `main_discussion` → `closing`) based on utterance counts and remaining time.
- **Scoring & Feedback**: Tracks user engagement (speaking time, point count) for post-session evaluation.

### Human-Like Dynamics
The system is optimized for real-time human interaction:
- **Responsive Interruptions**: User interruptions are acknowledged immediately rather than queued behind backlog messages.
- **Natural Pacing**: Prevents agents from speaking robotically or continuously dominating the floor upon session initiation.

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **Real-time Communication**: LiveKit (WebRTC)
- **AI Agents**: LiveKit Agents SDK (`livekit-agents`)
- **LLM Integrations**: Groq API, Google API (Gemini)
- **VAD (Voice Activity Detection)**: Silero
- **Frontend**: Vanilla HTML, CSS, JavaScript

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.11+
- A [LiveKit Cloud](https://cloud.livekit.io/) project or a local LiveKit server.
- API Keys for Groq and Google Gemini.

## Setup Instructions

### 1. Clone and Install Dependencies

Create a virtual environment (Python 3.11 recommended) and install the required dependencies:

```bash
# Create a virtual environment
python3.11 -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory of the project and configure the necessary environment variables:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=<your-api-key>
LIVEKIT_API_SECRET=<your-api-secret>

# LLM Providers
GROQ_API_KEY=<your-groq-api-key>
GOOGLE_API_KEY=<your-google-api-key>
```

## Running the Application

To start the GD Arena locally, you need to run both the web server and the agent workers.

### 1. Start the FastAPI Server

The FastAPI server serves the frontend UI and provides the API endpoints for session creation and token generation.

```bash
python server.py
```

*The server will start at `http://localhost:8000`.*

### 2. Start the Agent Workers

In a new terminal window (ensure the virtual environment is activated), run the agent launcher to start Kavya, Aarav, and Priya.

```bash
python run_agents.py
```

*Note: You can also start agents individually for debugging purposes using `python agents/moderator.py`, `python agents/debater_aarav.py`, or `python agents/debater_priya.py`.*

### 3. Join the Arena

Open your web browser and navigate to `http://localhost:8000`. Choose a topic, enter your name, and start the group discussion!

## Directory Structure

- `agents/`: Contains the logic and prompts for the AI personas (`moderator.py`, `debater_aarav.py`, `debater_priya.py`, etc.).
- `frontend/`: Contains the HTML, CSS, and JS files for the user interface.
- `server.py`: The main FastAPI server script.
- `run_agents.py`: A utility script to concurrently launch the AI agent workers.
- `shared_context.py`: Thread-safe context manager using LiveKit Room Metadata for shared memory and token reduction.
- `requirements.txt`: Python package dependencies.