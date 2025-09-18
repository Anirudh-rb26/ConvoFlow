import { NextRequest, NextResponse } from "next/server";
import { AccessToken, RoomServiceClient } from "livekit-server-sdk";

const livekitHost = process.env.LIVEKIT_URL!;
const apiKey = process.env.LIVEKIT_API_KEY!;
const apiSecret = process.env.LIVEKIT_API_SECRET!;

export async function POST(request: NextRequest) {
  try {
    const { room } = await request.json();
    const roomName = room || "chat-room";

    console.log(`🚀 Manually triggering agent for room: ${roomName}`);

    // Create room service client
    const roomService = new RoomServiceClient(livekitHost, apiKey, apiSecret);

    // Create agent token
    const agentToken = new AccessToken(apiKey, apiSecret, {
      identity: "gemini-agent",
      name: "Gemini AI Agent",
    });

    agentToken.addGrant({
      roomJoin: true,
      room: roomName,
      canPublish: true,
      canSubscribe: true,
    });

    const token = await agentToken.toJwt();

    // Try to dispatch agent job manually
    try {
      const participants = await roomService.listParticipants(roomName);
      console.log(`📊 Room ${roomName} has ${participants.length} participants`);

      // You might need to call a different API depending on your LiveKit setup
      // This is a placeholder - check LiveKit docs for agent job dispatch

      return NextResponse.json({
        success: true,
        message: "Agent trigger attempted",
        token: token,
        participants: participants.length,
      });
    } catch (error) {
      console.error("Error dispatching agent:", error);
      return NextResponse.json({
        success: false,
        error: "Failed to dispatch agent",
        token: token, // Still return token for manual testing
      });
    }
  } catch (error) {
    console.error("Error in agent trigger:", error);
    return NextResponse.json({ success: false, error: error }, { status: 500 });
  }
}
