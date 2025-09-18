import asyncio
import os
import json
from typing import List, Dict
from datetime import datetime
from livekit import agents, api
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
import google.generativeai as genai

# Configure APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class SimpleMemoryStore:
    def __init__(self):
        self.memory_file = "user_memories.json"
        self.memories = self.load_memories()
    
    def load_memories(self) -> Dict:
        """Load memories from JSON file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading memories: {e}")
        return {}
    
    def save_memories(self):
        """Save memories to JSON file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memories, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving memories: {e}")
    
    def get_user_context(self, username: str, limit: int = 5) -> str:
        """Get recent conversation context for user"""
        if username not in self.memories:
            return f"This is your first conversation with {username}."
        
        user_history = self.memories[username]
        recent_conversations = user_history[-limit:] if len(user_history) > limit else user_history
        
        if not recent_conversations:
            return f"This is your first conversation with {username}."
        
        context = f"Previous interactions with {username}:\n"
        for conv in recent_conversations:
            timestamp = conv.get('timestamp', 'Unknown time')
            user_msg = conv.get('user_message', '')
            bot_msg = conv.get('bot_response', '')
            context += f"[{timestamp}] User: {user_msg} | Bot: {bot_msg}\n"
        
        return context
    
    def save_interaction(self, username: str, user_message: str, bot_response: str):
        """Save interaction to memory"""
        if username not in self.memories:
            self.memories[username] = []
        
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'bot_response': bot_response
        }
        
        self.memories[username].append(interaction)
        
        # Keep only last 20 interactions per user to prevent memory overflow
        if len(self.memories[username]) > 20:
            self.memories[username] = self.memories[username][-20:]
        
        self.save_memories()

class ChatAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.memory = SimpleMemoryStore()
        self.room = None
    
    async def generate_response(self, username: str, user_message: str) -> str:
        """Generate AI response using Gemini with user context"""
        try:
            # Get user's conversation history
            context = self.memory.get_user_context(username)
            
            # Craft prompt with context
            prompt = f"""
You are a helpful AI assistant in a LiveKit chat room. Here's the context about your previous conversations:

{context}

Current user: {username}
User's message: {user_message}

Respond naturally and personally, acknowledging any relevant previous conversations if they exist. Keep responses conversational, engaging, and concise (1-3 sentences typically). If this is a first conversation, introduce yourself warmly.
"""
            
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            bot_response = response.text.strip()
            
            # Save this interaction for future reference
            self.memory.save_interaction(username, user_message, bot_response)
            
            return bot_response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, I'm having trouble processing your message right now. Please try again!"

chat_agent = ChatAgent()

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent"""
    initial_ctx = ctx.job.room.url or ctx.job.room.name
    print(f"🤖 AI Agent connecting to room: {initial_ctx}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    chat_agent.room = ctx.room
    
    # Send welcome message
    await ctx.room.local_participant.publish_data(
        "🤖 AI Assistant has joined the chat! I remember our previous conversations. Say hello!",
        reliable=True
    )
    print("🤖 Welcome message sent")
    
    @ctx.room.on("data_received")
    async def on_data_received(data: api.DataPacket):
        """Handle incoming text messages"""
        if data.participant.identity == ctx.room.local_participant.identity:
            return  # Ignore messages from the agent itself
        
        username = data.participant.identity
        message = data.data.decode('utf-8')
        
        print(f"📨 [{username}]: {message}")
        
        # Generate AI response with memory
        response = await chat_agent.generate_response(username, message)
        
        # Send response back to the room
        await ctx.room.local_participant.publish_data(
            response,
            reliable=True
        )
        
        print(f"🤖 [Bot]: {response}")
    
    print("🤖 Agent is ready and listening for messages...")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )