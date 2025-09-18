
import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc
import google.generativeai as genai
import jwt
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiAgent:
    def __init__(self):
        self.room = None
        self.model = None
        self.setup_gemini()

    def setup_gemini(self):
        """Initialize Gemini API"""
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.info("✅ Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            raise

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
        """Debug version with extensive logging"""
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

        # Data message handler - ENHANCED VERSION
        @self.room.on("data_received")
        def on_data_received(data_packet: rtc.DataPacket):
            logger.info(f"🔥 DATA RECEIVED EVENT FIRED!")
            logger.info(f"📨 Raw data: {data_packet.data}")

            # Enhanced participant resolution
            participant_identity = self.get_participant_identity(data_packet)
            logger.info(f"👤 From participant: {participant_identity}")
            logger.info(f"📋 Topic: {data_packet.topic}")

            # Additional debugging info
            logger.debug(f"🔍 Data packet participant object: {data_packet.participant}")
            logger.debug(f"🔍 Has participant attribute: {hasattr(data_packet, 'participant')}")
            if hasattr(data_packet, 'participant_sid'):
                logger.debug(f"🔍 Participant SID: {getattr(data_packet, 'participant_sid', 'Not available')}")

            # Log all remote participants for debugging
            remote_participants = list(self.room.remote_participants.values())
            logger.debug(f"🔍 All remote participants: {[(p.identity, p.sid) for p in remote_participants]}")

            # Process the message asynchronously with resolved identity
            asyncio.create_task(self.handle_message(data_packet.data, participant_identity))

        # Participant events
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"👋 New participant joined: {participant.identity} (SID: {participant.sid})")
            asyncio.create_task(self.send_welcome_message(participant))

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

    async def handle_message(self, data: bytes, sender_identity: str = "Unknown"):
        """Handle incoming text messages and respond with Gemini"""
        try:
            # Decode the message
            message = data.decode('utf-8')

            logger.info(f"💬 PROCESSING MESSAGE from {sender_identity}: '{message}'")

            # Skip messages from agents/bots to avoid loops
            if any(keyword in sender_identity.lower() for keyword in ["agent", "bot", "gemini", "ai"]):
                logger.info(f"⏭️ Ignoring message from agent: {sender_identity}")
                return

            # Generate response using Gemini
            logger.info("🧠 Generating response with Gemini...")
            try:
                prompt = f"""You are a helpful AI assistant in a chat room. 
A user named {sender_identity} just sent you this message: "{message}"

Please provide a helpful, concise, and engaging response (max 2-3 sentences).
Keep it conversational and friendly."""

                response = self.model.generate_content(prompt)
                gemini_response = response.text.strip()

                logger.info(f"✅ Generated response: {gemini_response}")

            except Exception as e:
                logger.error(f"❌ Error with Gemini API: {e}")
                gemini_response = f"Hi {sender_identity}! I'm having some technical difficulties right now, but I'm here and ready to help. Please try asking me something else!"

            # Send response back to the room
            await self.send_message(gemini_response)

        except Exception as e:
            logger.error(f"❌ Error handling message: {e}", exc_info=True)

    async def send_message(self, message: str):
        """Send a message to the room"""
        try:
            await self.room.local_participant.publish_data(
                payload=message.encode('utf-8'),
                reliable=True
            )
            logger.info("📤 Message sent successfully to room")
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")

    async def send_welcome_message(self, participant: rtc.RemoteParticipant = None):
        """Send welcome message"""
        try:
            await asyncio.sleep(1)  # Small delay
            if participant:
                welcome = f"👋 Welcome {participant.identity}! I'm an AI assistant powered by Gemini. Send me a message to chat!"
            else:
                welcome = "🤖 AI Assistant powered by Gemini has joined! Send me a message and I'll respond."

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
            logger.info("🎉 Agent is ready and listening for messages!")
            logger.info("📱 Try sending a data message from your client...")

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
    logger.info("🔧 Starting LiveKit Gemini Chat Agent...")

    # Check required environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GEMINI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return

    logger.info(f"🌐 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    logger.info(f"🔑 LiveKit API Key: {os.getenv('LIVEKIT_API_KEY')[:8]}...")
    logger.info(f"🔑 Gemini API Key: {'*' * 8}{os.getenv('GEMINI_API_KEY', '')[-4:]}")

    # Create and run agent
    agent = GeminiAgent()

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("🛑 Agent stopped by user")
    except Exception as e:
        logger.error(f"❌ Agent failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
