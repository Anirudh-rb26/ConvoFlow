# ConvoFlow - Memory-Enhanced AI Chat with LiveKit

ConvoFlow is a real-time AI chat system that combines LiveKit's real-time communication capabilities with memory-enhanced contextual conversations using Mem0 and Google's Gemini AI.

## Features

- **Real-time Chat**: Built on LiveKit for robust real-time communication
- **Memory-Enhanced Conversations**: Uses Mem0 for persistent memory across chat sessions
- **AI Integration**: Powered by Google's Gemini AI for intelligent responses
- **Context-Aware**: Maintains conversation context across multiple sessions
- **Special Commands**:
  - `dump memories`: View all stored memories
  - `clear memory`: Reset stored memories
  - `show all`: Alternative command to view memories
  - `list memories`: Another way to view stored memories

## Project Structure

```
ConvoFlow/
├── convoflow-backend/         # Python backend with LiveKit Agent
│   ├── echo_agent.py         # Main agent implementation
│   ├── requirements.txt      # Python dependencies
├── convoflow-frontend/       # Next.js frontend
    ├── app/                  # Next.js app directory
    ├── components/          # UI components
    └── lib/                 # Utilities and helpers
```

## Prerequisites

- Python 3.8+
- Node.js 18+
- LiveKit server access
- Mem0 API key
- Google Gemini API key

## Environment Setup

### Backend (.env in convoflow-backend)

```env
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret
GEMINI_API_KEY=your_gemini_api_key
MEM0_API_KEY=your_mem0_api_key
```

### Frontend (.env in convoflow-frontend)

```env
NEXT_PUBLIC_LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret
```

## Installation

### Backend Setup

1. Navigate to the backend directory:

   ```bash
   cd convoflow-backend
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. Navigate to the frontend directory:

   ```bash
   cd convoflow-frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Start the Backend

1.  Make sure you're in the backend directory with the virtual environment activated

    ```bash
    cd convoflow-backend
    ```

2.  Run the agent:
    ```bash
    py echo_agent.py dev
    ```

### Start the Frontend

1. In the frontend directory:

   ```bash
   npm run dev
   ```

2. Access the application at `http://localhost:3000`

## Usage

1. Open the application in your browser
2. Enter your username to join the chat
3. Start chatting with the AI agent
4. Use special commands to manage memories:
   - Type "dump memories" to see all stored memories
   - Type "clear memory" to reset your memory context
   - Chat normally for context-aware conversations

## Memory System

The system uses Mem0 for maintaining conversation context:

- **Storage**: Each conversation is automatically stored with user context
- **Retrieval**: Relevant memories are retrieved based on conversation context
- **Fallback**: Enhanced memory retrieval with smart fallback mechanisms
- **Persistence**: Memories persist across multiple chat sessions

## Advanced Features

### Smart Memory Retrieval

The system implements sophisticated memory retrieval with:

- Contextual search based on conversation topics
- Smart fallback for comprehensive memory access
- Preference and identity-aware memory retrieval

### Welcome Messages

- New users receive a standard welcome
- Returning users get personalized greetings based on stored memories

### Error Handling

- Graceful degradation when services are unavailable
- Automatic retry mechanisms for failed operations
- Comprehensive logging for troubleshooting
