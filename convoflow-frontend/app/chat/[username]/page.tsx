"use client";

import { Send } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useParams } from "next/navigation";

import React, { useEffect, useRef, useState } from "react";
import { RemoteParticipant, Room, RoomEvent } from "livekit-client";
import { Button } from "@/components/ui/button";

interface Message {
    sender: string | "BOT";
    text: string;
}

const ChatPage = () => {
    const params = useParams();
    const username = decodeURIComponent(params.username as string)

    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);

    // LiveKit
    const [room, setRoom] = useState<Room | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState("Connecting...");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }

    const handleSendMessage = async () => {
        if (!message.trim() || !room || !isConnected) return;

        setMessages(prev => [...prev, { sender: username, text: message }]);

        const encoder = new TextEncoder();
        await room?.localParticipant.publishData(
            encoder.encode(message),
            { reliable: true }
        );

        setMessage(""); // Clear the input after sending
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        const connectToRoom = async () => {
            try {
                setConnectionStatus("Fetching Room Details...");

                const response = await fetch('/api/livekit-token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        room: 'chat-room' // You can make this dynamic if needed
                    }),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`Failed to fetch token: ${response.status} ${errorText}`);
                }

                const responseData = await response.json();
                console.log('API Response:', responseData);

                const { token } = responseData;

                if (!token) {
                    throw new Error('No token received from API');
                }

                console.log('Token received:', token ? 'Token exists' : 'No token');

                setConnectionStatus("Establishing Connection...");

                const newRoom = new Room();

                newRoom.on(RoomEvent.Connected, () => {
                    console.log('Connected to Room')
                    setIsConnected(true);
                    setConnectionStatus("Connected");

                    setMessages(prev => [{ sender: "BOT", text: "You are now connected to the chat!" }, ...prev]);
                });

                newRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
                    const receivedMessage = new TextDecoder().decode(payload);
                    const senderName = participant?.identity || "BOT";

                    console.log(`Message from ${senderName}: ${receivedMessage}`);

                    setMessages(prev => [...prev, { sender: senderName, text: receivedMessage }]);
                });

                newRoom.on(RoomEvent.Disconnected, () => {
                    console.log('Disconnected from Room');
                    setIsConnected(false);
                    setConnectionStatus("Disconnected");
                });

                newRoom.on(RoomEvent.Reconnecting, () => {
                    setConnectionStatus("Reconnecting...");
                });

                newRoom.on(RoomEvent.Reconnected, () => {
                    setConnectionStatus("Connected");
                });

                // Use the NEXT_PUBLIC_ prefixed environment variable
                const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;

                if (!livekitUrl) {
                    throw new Error('LiveKit URL not configured');
                }

                await newRoom.connect(livekitUrl, token);
                setRoom(newRoom);

            } catch (error) {
                console.error("Error Connecting to Room", error);
                setConnectionStatus("Connection Failed");
                setMessages(prev => [{
                    sender: "BOT",
                    text: "Failed to connect to chat room. Please refresh and try again."
                }, ...prev]);
            }
        };

        connectToRoom();

        // Cleanup
        return () => {
            if (room) {
                room.disconnect();
            }
        };
    }, [username]);


    return (
        <div className="flex flex-col h-screen bg-black text-white max-w-screen mx-auto">
            {/* Header */}
            <div className="p-3 sm:p-4 border-b border-gray-800 text-center text-base sm:text-lg font-semibold sticky top-0 bg-black">
                {username}&apos;s Chat
                <div className={`text-xs mt-1 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                    {connectionStatus}
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-500 text-sm sm:text-base">
                        No messages yet. Start a conversation!
                    </div>
                ) : (
                    messages.map((message, index) => (
                        <div key={index} className={`flex ${message.sender === "BOT" ? "" : "justify-end"}`} >
                            <div className={`sm:max-w-xs md:max-w-sm lg:max-w-md rounded-2xl px-3 sm:px-4 py-2 text-sm sm:text-base ${message.sender === "BOT" ? "bg-[#26252A] text-white" : "bg-blue-500 text-white"}`}>
                                {message.text}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-3 sm:p-4 border-t border-gray-800 flex items-center space-x-2 bg-black">
                <Input
                    type="text"
                    placeholder="Type a message..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    className="flex-1 px-3 sm:px-4 py-2 rounded-full bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus-visible:ring-blue-500 text-sm sm:text-base"
                />
                <Button
                    onClick={handleSendMessage}
                    className="p-2 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={!isConnected || !message.trim()}
                >
                    <Send className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </Button>
            </div>
        </div>
    );
};

export default ChatPage;