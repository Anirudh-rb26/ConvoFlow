import { AccessToken } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { room, username } = await request.json();

    if (!room || !username) {
      return NextResponse.json({ error: "Room and Username Required" }, { status: 400 });
    }

    if (!process.env.LIVEKIT_API_KEY || !process.env.LIVEKIT_API_SECRET) {
      console.error("Missing LiveKit credentials");
      return NextResponse.json({ error: "Server configuration error" }, { status: 500 });
    }

    const token = new AccessToken(process.env.LIVEKIT_API_KEY, process.env.LIVEKIT_API_SECRET, {
      identity: username,
      name: username,
    });

    token.addGrant({
      room,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    });

    const jwt = await token.toJwt();

    return NextResponse.json({ token: jwt });
  } catch (error) {
    console.error("Failed to generate Token", error);
    return NextResponse.json({ error: "Failed to generate Token" }, { status: 500 });
  }
}
