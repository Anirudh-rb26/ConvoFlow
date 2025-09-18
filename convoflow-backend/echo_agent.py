import asyncio
import os
from typing import List, Dict
from livekit import agents, api
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
import google.generativeai as genai
from mem0 import Memory

# Configure APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
memory_client = Memory()

class ChatAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.room = None
    
    async def get_user_context(self, username: str) -> str:
        """Retrieve user's conversation history from mem0"""
        try:
            # Search for relevant memories for this user
            memories = memory_client.search(
                query=f"user:{username} conversations",
                user_id=username,
                limit=5
            )
            
            if not memories:
                return f"This is your first conversation with {username}."
            
            context = f"Previous interactions with {username}:\n"
            for memory in memories:
                context += f"- {memory['text']}\n"
            
            return context
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return f"Unable to retrieve conversation history for {username}."
    
    async def save_interaction(self, username: str, user_message: str, bot_response: str):
        """Save the interaction to mem0 for future reference"""
        try:
            interaction_text = f"User said: '{user_message}' | Bot replied: '{bot_response}'"
            memory_client.add(
                messages=[{"content": interaction_text, "role": "user"}],
                user_id=username,
                metadata={"type": "conversation", "username": username}
            )
        except Exception as e:
            print(f"Error saving interaction: {e}")
    
    async def generate_response(self, username: str, user_message: str) -> str:
        """Generate AI response using Gemini with user context"""
        try:
            # Get user's conversation history
            context = await self.get_user_context(username)
            
            # Craft prompt with context
            prompt = f"""
You are a helpful AI assistant in a LiveKit chat room. Here's the context:

{context}

Current user: {username}
User's message: {user_message}

Respond naturally and personally, acknowledging any relevant previous conversations. Keep responses conversational and engaging.
"""
            
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            bot_response = response.text.strip()
            
            # Save this interaction for future reference
            await self.save_interaction(username, user_message, bot_response)
            
            return bot_response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, I'm having trouble processing your message right now."

chat_agent = ChatAgent()

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent"""
    initial_ctx = ctx.job.room.url or ctx.job.room.name
    print(f"Connecting to room: {initial_ctx}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    chat_agent.room = ctx.room
    
    # Send welcome message
    await ctx.room.local_participant.publish_data(
        "🤖 AI Assistant has joined the chat! I remember our previous conversations.",
        reliable=True
    )
    
    @ctx.room.on("data_received")
    async def on_data_received(data: api.DataPacket):
        """Handle incoming text messages"""
        if data.participant.identity == ctx.room.local_participant.identity:
            return  # Ignore messages from the agent itself
        
        username = data.participant.identity
        message = data.data.decode('utf-8')
        
        print(f"[{username}]: {message}")
        
        # Generate AI response with memory
        response = await chat_agent.generate_response(username, message)
        
        # Send response back to the room
        await ctx.room.local_participant.publish_data(
            f"🤖 {response}",
            reliable=True
        )
        
        print(f"[Bot]: {response}")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            ws_url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET")
        )
    )