import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc
import google.generativeai as genai
import jwt
import time
from mem0 import AsyncMemoryClient
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiAgentWithMemory:
    def __init__(self):
        self.room = None
        self.model = None
        self.memory_client = None
        self.setup_gemini()
        self.setup_mem0()

    def setup_gemini(self):
        """Initialize Gemini API"""
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.info("✅ Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise

    def setup_mem0(self):
        """Initialize Mem0 memory client"""
        try:
            # Initialize Mem0 async client
            self.memory_client = AsyncMemoryClient(
                api_key=os.getenv("MEM0_API_KEY")
            )
            logger.info("✅ Mem0 memory client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Mem0: {e}")
            # Fall back to non-memory mode if Mem0 fails
            self.memory_client = None

    async def connect_to_room(self, room_name="chat-room", identity="gemini-agent"):
        """Connect to LiveKit room"""
        try:
            # Generate JWT token
            token = self.generate_token(room_name, identity)

            # Connect to room
            self.room = rtc.Room()
            await self.room.connect(os.getenv("LIVEKIT_URL"), token)
            logger.info(f"✅ Connected to room: {room_name}")

            # Set up event handlers
            self.setup_event_handlers()

            return self.room
        except Exception as e:
            logger.error(f"❌ Failed to connect to room: {e}")
            raise

    def generate_token(self, room_name, identity):
        """Generate JWT token for room access"""
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")

        if not api_key or not api_secret:
            raise ValueError("Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET")

        token = jwt.encode(
            {
                "iss": api_key,
                "exp": int(time.time()) + 3600,
                "nbf": int(time.time()),
                "video": {
                    "room": room_name,
                    "roomJoin": True,
                    "canPublish": True,
                    "canSubscribe": True,
                    "canPublishData": True,
                },
                "sub": identity,
            },
            api_secret,
            algorithm="HS256",
        )

        return token

    def get_participant_identity(self, data_packet: rtc.DataPacket):
        """Get participant identity with enhanced logging"""
        logger.info("🔍 === get_participant_identity() CALLED ===")
        
        # Log the data packet details
        logger.info(f"🔍 data_packet: {data_packet}")
        logger.info(f"🔍 data_packet.participant: {getattr(data_packet, 'participant', 'MISSING')}")
        
        # Check remote participants
        remote_participants = list(self.room.remote_participants.values())
        logger.info(f"🔍 remote_participants count: {len(remote_participants)}")
        logger.info(f"🔍 remote_participants identities: {[p.identity for p in remote_participants]}")
        
        # Try the simple logic
        if len(remote_participants) == 1:
            identity = remote_participants[0].identity
            logger.info(f"🔍 FOUND single participant: {identity}")
            return identity
        elif len(remote_participants) > 1:
            # Find first non-agent
            for participant in remote_participants:
                identity = participant.identity
                if not any(keyword in identity.lower() for keyword in ["agent", "bot", "gemini", "ai"]):
                    logger.info(f"🔍 FOUND non-agent participant: {identity}")
                    return identity
        
        logger.warning("🔍 FALLBACK: Returning Unknown")
        return "Unknown"

    def setup_event_handlers(self):
        """Set up all event handlers for the room"""

        # Data message handler - ENHANCED VERSION WITH MEMORY
        @self.room.on("data_received")
        def on_data_received(data_packet: rtc.DataPacket):
            logger.info(f"🔥 DATA RECEIVED EVENT FIRED!")
            logger.info(f"📨 Raw data: {data_packet.data}")

            # Enhanced participant resolution
            participant_identity = self.get_participant_identity(data_packet)
            logger.info(f"👤 From participant: {participant_identity}")
            logger.info(f"📋 Topic: {data_packet.topic}")

            # Process the message asynchronously with resolved identity
            # FIXED: Don't create new task, await directly to ensure proper execution order
            asyncio.ensure_future(self.handle_message(data_packet.data, participant_identity))

        # Participant events
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"👋 New participant joined: {participant.identity} (SID: {participant.sid})")
            asyncio.ensure_future(self.send_welcome_message(participant))

        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"👋 Participant left: {participant.identity} (SID: {participant.sid})")

        # Track published/unpublished for debugging
        @self.room.on("track_published")
        def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            logger.info(f"🎵 Track published by {participant.identity}: {publication.kind}")

        # Room connection state changes
        @self.room.on("connection_state_changed")
        def on_connection_state_changed(state: rtc.ConnectionState):
            logger.info(f"🔗 Connection state changed to: {state}")

        logger.info("✅ All event handlers registered")

    async def retrieve_memories(self, query: str, user_id: str) -> str:
        """Retrieve relevant memories from Mem0"""
        if not self.memory_client:
            return ""
            
        try:
            logger.info(f"🧠 Retrieving memories for user {user_id} with query: {query}")
            
            # Search for relevant memories
            search_results = await self.memory_client.search(
                query=query,
                user_id=user_id,
                limit=10  # Increased limit for better recall
            )
            
            if search_results and 'results' in search_results:
                memories = []
                for result in search_results['results']:
                    memory_content = result.get('memory', '')
                    if memory_content:
                        memories.append(f"- {memory_content}")
                
                if memories:
                    memory_context = "\n".join(memories)
                    logger.info(f"✅ Retrieved {len(memories)} relevant memories")
                    return f"Relevant memories about this user:\n{memory_context}\n\n"
            
            logger.info("ℹ️ No relevant memories found")
            return ""
            
        except Exception as e:
            logger.error(f"❌ Error retrieving memories: {e}")
            return ""

    async def get_all_memories(self, user_id: str) -> str:
        """Get all memories for a user - for dump commands"""
        if not self.memory_client:
            return "Memory system not available."
            
        try:
            logger.info(f"🗄️ Getting ALL memories for user {user_id}")
            
            # Get all memories using the get_all method
            all_memories_response = await self.memory_client.get_all(user_id=user_id)
            
            if all_memories_response and isinstance(all_memories_response, list):
                if len(all_memories_response) == 0:
                    return "No memories found for this user."
                
                memories = []
                for i, memory_obj in enumerate(all_memories_response, 1):
                    # Handle different response formats
                    if isinstance(memory_obj, dict):
                        memory_text = memory_obj.get('memory', memory_obj.get('text', str(memory_obj)))
                        created_at = memory_obj.get('created_at', 'Unknown time')
                        memories.append(f"{i}. {memory_text} (Created: {created_at})")
                    else:
                        memories.append(f"{i}. {str(memory_obj)}")
                
                memory_dump = "\n".join(memories)
                logger.info(f"✅ Retrieved {len(memories)} total memories")
                return f"📋 All stored memories for {user_id}:\n\n{memory_dump}"
            else:
                return "No memories found or unexpected response format."
                
        except Exception as e:
            logger.error(f"❌ Error getting all memories: {e}")
            return f"Error retrieving memories: {str(e)}"

    async def store_conversation(self, user_message: str, assistant_response: str, user_id: str):
        """Store the conversation in Mem0 memory"""
        if not self.memory_client:
            return
            
        try:
            logger.info(f"💾 Storing conversation for user {user_id}")
            
            # Format conversation as messages
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]
            
            # Add to Mem0 memory
            result = await self.memory_client.add(
                messages=messages,
                user_id=user_id,
                metadata={
                    "source": "livekit_chat",
                    "timestamp": int(time.time())
                }
            )
            
            logger.info("✅ Conversation stored in memory successfully")
            logger.debug(f"📝 Memory storage result: {result}")
            
        except Exception as e:
            logger.error(f"❌ Error storing conversation: {e}")

    async def handle_message(self, data: bytes, sender_identity: str = "Unknown"):
        """Handle incoming text messages with memory integration"""
        try:
            # Decode the message
            message = data.decode('utf-8')

            logger.info(f"💬 PROCESSING MESSAGE from {sender_identity}: '{message}'")

            # Skip messages from agents/bots to avoid loops
            if any(keyword in sender_identity.lower() for keyword in ["agent", "bot", "gemini", "ai"]):
                logger.info(f"⏭️ Ignoring message from agent: {sender_identity}")
                return

            # Check for special commands
            message_lower = message.lower().strip()
            
            # Handle memory dump commands
            if any(cmd in message_lower for cmd in ["dump", "show all", "list memories", "all memories"]):
                logger.info("🗄️ Processing memory dump command")
                memories_dump = await self.get_all_memories(sender_identity)
                await self.send_message(memories_dump)
                return
            
            # Handle memory clear commands
            if any(cmd in message_lower for cmd in ["clear memory", "forget", "reset memory"]):
                if self.memory_client:
                    try:
                        # Delete all memories for this user
                        await self.memory_client.delete_all(user_id=sender_identity)
                        response = f"🧹 All memories cleared for {sender_identity}!"
                    except Exception as e:
                        response = f"❌ Error clearing memories: {str(e)}"
                else:
                    response = "❌ Memory system not available."
                
                await self.send_message(response)
                return

            # Retrieve relevant memories for this user
            memory_context = await self.retrieve_memories(message, sender_identity)

            # Generate response using Gemini with memory context
            logger.info("🧠 Generating response with Gemini and memory context...")
            
            try:
                # Enhanced prompt with memory context
                if memory_context:
                    prompt = f"""You are a helpful AI assistant in a chat room with memory capabilities.

{memory_context}User {sender_identity} just sent: "{message}"

Respond naturally and conversationally (1-2 sentences max). If you have relevant memories, reference them naturally. Be friendly and helpful."""
                else:
                    prompt = f"""You are a helpful AI assistant in a chat room.

User {sender_identity} just sent: "{message}"

Respond naturally and conversationally (1-2 sentences max). Be friendly and helpful."""

                # FIXED: Add timeout and proper error handling for Gemini
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.model.generate_content, prompt),
                    timeout=30.0  # 30 second timeout
                )
                gemini_response = response.text.strip()

                logger.info(f"✅ Generated response: {gemini_response}")

            except asyncio.TimeoutError:
                logger.error("❌ Gemini API timeout")
                gemini_response = f"Hi {sender_identity}! I'm taking a bit longer to respond than usual. Let me try again - what can I help you with?"
            except Exception as e:
                logger.error(f"❌ Error with Gemini API: {e}")
                gemini_response = f"Hi {sender_identity}! I'm having some technical difficulties right now, but I'm here and ready to help. Please try asking me something else!"

            # FIXED: Send response immediately, then store in background
            await self.send_message(gemini_response)

            # Store conversation in background (don't await to avoid delays)
            asyncio.ensure_future(self.store_conversation(message, gemini_response, sender_identity))

        except Exception as e:
            logger.error(f"❌ Error handling message: {e}", exc_info=True)
            # Send error response to user
            try:
                await self.send_message(f"Sorry {sender_identity}, I encountered an error processing your message. Please try again.")
            except:
                pass

    async def send_message(self, message: str):
        """Send a message to the room with improved error handling"""
        try:
            # FIXED: Add small delay and ensure message is sent immediately
            await self.room.local_participant.publish_data(
                payload=message.encode('utf-8'),
                reliable=True,
                topic=""  # Ensure empty topic
            )
            logger.info(f"📤 Message sent successfully: '{message[:50]}...'")
            
            # FIXED: Add small delay to ensure message is processed
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            # Retry once
            try:
                await asyncio.sleep(0.5)
                await self.room.local_participant.publish_data(
                    payload=message.encode('utf-8'),
                    reliable=True
                )
                logger.info("📤 Message sent successfully on retry")
            except Exception as retry_error:
                logger.error(f"❌ Failed to send message on retry: {retry_error}")

    async def send_welcome_message(self, participant: rtc.RemoteParticipant = None):
        """Send welcome message with memory awareness"""
        try:
            await asyncio.sleep(1)  # Small delay
            
            if participant:
                # Try to retrieve any existing memories about this user
                user_memories = await self.retrieve_memories("", participant.identity)
                
                if user_memories:
                    welcome = f"👋 Welcome back {participant.identity}! I remember our previous conversations. How can I help you today?"
                else:
                    welcome = f"👋 Welcome {participant.identity}! I'm an AI assistant with memory. I'll remember our conversations. Say 'dump memories' to see what I know, or just chat normally!"
            else:
                welcome = "🤖 AI Assistant with Memory has joined! Try: 'dump memories', 'clear memory', or just chat with me!"

            await self.send_message(welcome)
            logger.info(f"✅ Welcome message sent")
        except Exception as e:
            logger.error(f"❌ Failed to send welcome message: {e}")

    async def run(self):
        """Main run loop"""
        try:
            await self.connect_to_room()

            # Send initial welcome message
            await asyncio.sleep(2)
            await self.send_welcome_message()

            # Log current state
            participants = list(self.room.remote_participants.values())
            logger.info(f"📊 Current participants: {[f'{p.identity} (SID: {p.sid})' for p in participants]}")
            logger.info(f"🆔 Agent identity: {self.room.local_participant.identity}")
            logger.info("🎉 Agent with Memory is ready and listening!")
            logger.info("📱 Try commands: 'dump memories', 'clear memory', or just chat normally")

            # Keep running with periodic status updates
            counter = 0
            while self.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.sleep(10)
                counter += 1
                logger.info(f"💓 Agent heartbeat #{counter} - Connection: {self.room.connection_state}")

                # Log participants for debugging
                participants = list(self.room.remote_participants.values())
                logger.debug(f"📊 Active participants: {[p.identity for p in participants]}")

                # If we have participants but no messages, log a reminder
                if participants and counter % 6 == 0:  # Every minute
                    logger.warning("⚠️ Participants connected but no messages received. Check client implementation.")

        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}", exc_info=True)
            raise

def main():
    """Main entry point"""
    logger.info("🔧 Starting LiveKit Gemini Chat Agent with Memory...")

    # Check required environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GEMINI_API_KEY"]
    optional_vars = ["MEM0_API_KEY"]  # Mem0 is optional
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        return

    # Check optional variables
    if not os.getenv("MEM0_API_KEY"):
        logger.warning("⚠️ MEM0_API_KEY not found - running without persistent memory")

    logger.info(f"🌐 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    logger.info(f"🔑 LiveKit API Key: {os.getenv('LIVEKIT_API_KEY')[:8]}...")
    logger.info(f"🔑 Gemini API Key: {'*' * 8}{os.getenv('GEMINI_API_KEY', '')[-4:]}")
    
    if os.getenv("MEM0_API_KEY"):
        logger.info(f"🧠 Mem0 API Key: {'*' * 8}{os.getenv('MEM0_API_KEY', '')[-4:]}")

    # Create and run agent
    agent = GeminiAgentWithMemory()

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("🛑 Agent stopped by user")
    except Exception as e:
        logger.error(f"❌ Agent failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()