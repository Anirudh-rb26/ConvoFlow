import { AccessToken } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { room, username } = await request.json();

    console.log("=== DETAILED DEBUG ===");
    console.log("Request body:", { room, username });
    console.log("LIVEKIT_API_KEY:", process.env.LIVEKIT_API_KEY);
    console.log("LIVEKIT_API_SECRET length:", process.env.LIVEKIT_API_SECRET?.length);
    console.log("Expected API key: APIdNBxnBTadm5Y");
    console.log("Keys match:", process.env.LIVEKIT_API_KEY === "APIdNBxnBTadm5Y");

    console.log("=== ENVIRONMENT DEBUG ===");
    console.log(
      "All process.env keys:",
      Object.keys(process.env).filter((k) => k.includes("LIVE"))
    );
    console.log("NODE_ENV:", process.env.NODE_ENV);
    console.log("Raw LIVEKIT_API_KEY:", JSON.stringify(process.env.LIVEKIT_API_KEY));
    console.log("Raw LIVEKIT_API_SECRET:", JSON.stringify(process.env.LIVEKIT_API_SECRET));

    // Check if there are any LIVEKIT variables in the environment
    Object.keys(process.env).forEach((key) => {
      if (key.includes("LIVEKIT") || key.includes("livekit")) {
        console.log(`${key}: ${process.env[key]}`);
      }
    });

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

    // Decode and inspect the JWT
    const parts = jwt.split(".");
    if (parts.length === 3) {
      const payload = JSON.parse(Buffer.from(parts[1], "base64").toString());
      console.log("=== JWT PAYLOAD ===");
      console.log("Issuer (iss):", payload.iss);
      console.log("Subject (sub):", payload.sub);
      console.log("Room:", payload.video?.room);
      console.log("Full payload:", JSON.stringify(payload, null, 2));
    }

    console.log(`Token generated successfully for user: ${username} in room: ${room}`);

    return NextResponse.json({ token: jwt });
  } catch (error) {
    console.error("Failed to generate Token", error);
    return NextResponse.json({ error: "Failed to generate Token" }, { status: 500 });
  }
}
