"""
Simple test agent - save this as test_agent.py
This is a minimal version to test if the entrypoint gets called at all
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit import rtc

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def entrypoint(ctx: JobContext):
    """Minimal entrypoint - just log that we got called"""
    logger.info("🎉🎉🎉 ENTRYPOINT CALLED! AGENT IS WORKING! 🎉🎉🎉")
    logger.info(f"Room: {ctx.room.name}")
    logger.info(f"Job ID: {ctx.job.id}")
    
    try:
        # Connect to room
        await ctx.connect(auto_subscribe=True)
        logger.info("✅ Connected to room")
        
        # Set up a simple data handler
        @ctx.room.on("data_received")
        def on_data_received(data_packet: rtc.DataPacket):
            message = data_packet.data.decode('utf-8')
            sender = data_packet.participant.identity if data_packet.participant else "Unknown"
            logger.info(f"📨 Received: '{message}' from {sender}")
            
            # Echo back the message with a prefix
            echo_message = f"🤖 Echo: {message}"
            asyncio.create_task(send_echo(echo_message))
        
        async def send_echo(message: str):
            try:
                data = message.encode('utf-8')
                await ctx.room.local_participant.publish_data(data)
                logger.info(f"📤 Sent echo: {message}")
            except Exception as e:
                logger.error(f"❌ Echo failed: {e}")
        
        # Send welcome message
        await send_echo("🤖 Simple test agent connected!")
        
        # Keep alive
        while True:
            await asyncio.sleep(10)
            logger.info("💓 Test agent heartbeat")
            
    except Exception as e:
        logger.error(f"❌ Error in test agent: {e}", exc_info=True)

def main():
    logger.info("🧪 Starting SIMPLE TEST AGENT...")
    
    # Check environment
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"❌ Missing env vars: {missing}")
        return
    
    logger.info(f"🌐 LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    
    # Simple worker options
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
        # Try to accept any job
        request_fnc=lambda req: True,
    )
    
    cli.run_app(worker_options)

if __name__ == "__main__":
    main()