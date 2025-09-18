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
    timestamp: Date;
}

const ChatPage = () => {
    const params = useParams();
    const username = decodeURIComponent(params.username as string);

    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);

    // LiveKit
    const [room, setRoom] = useState<Room | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState("Connecting...");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const addMessage = (sender: string, text: string) => {
        setMessages(prev => [...prev, {
            sender,
            text,
            timestamp: new Date()
        }]);
    };

    const handleSendMessage = async () => {
        if (!message.trim() || !room || !isConnected) return;

        try {
            // Add user message to UI immediately
            addMessage(username, message);

            // Send message through LiveKit
            const encoder = new TextEncoder();
            await room.localParticipant.publishData(
                encoder.encode(message),
                { reliable: true }
            );

            setMessage(""); // Clear the input after sending
        } catch (error) {
            console.error("Error sending message:", error);
            addMessage("SYSTEM", "Failed to send message. Please try again.");
        }
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
                        room: 'chat-room'
                    }),
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', response.status, errorText);
                    throw new Error(`Failed to fetch token: ${response.status} ${errorText}`);
                }

                const responseData = await response.json();
                // console.log('API Response:', responseData);

                const { token } = responseData;

                if (!token) {
                    throw new Error('No token received from API');
                }

                setConnectionStatus("Establishing Connection...");

                const newRoom = new Room();

                newRoom.on(RoomEvent.Connected, () => {
                    // console.log('Connected to Room');
                    setIsConnected(true);
                    setConnectionStatus("Connected");
                    addMessage("SYSTEM", "Connected to chat room successfully!");
                });

                newRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
                    try {
                        const receivedMessage = new TextDecoder().decode(payload);
                        const senderName = participant?.identity || "BOT";

                        // console.log(`Message from ${senderName}: ${receivedMessage}`);

                        // Only add message if it's not from the current user (to avoid duplicates)
                        if (senderName !== username) {
                            addMessage(senderName, receivedMessage);
                        }
                    } catch (error) {
                        console.error("Error processing received message:", error);
                    }
                });

                newRoom.on(RoomEvent.Disconnected, () => {
                    // console.log('Disconnected from Room:', reason);
                    setIsConnected(false);
                    setConnectionStatus("Disconnected");
                    addMessage("SYSTEM", "Disconnected from chat room.");
                });

                newRoom.on(RoomEvent.Reconnecting, () => {
                    setConnectionStatus("Reconnecting...");
                    addMessage("SYSTEM", "Reconnecting to chat room...");
                });

                newRoom.on(RoomEvent.Reconnected, () => {
                    setConnectionStatus("Connected");
                    addMessage("SYSTEM", "Reconnected successfully!");
                });

                // newRoom.on(RoomEvent.ConnectionQualityChanged, (quality, participant) => {
                //     console.log('Connection quality changed:', quality, participant?.identity);
                // });

                // Handle participant events
                newRoom.on(RoomEvent.ParticipantConnected, (participant) => {
                    // console.log('Participant connected:', participant.identity);
                    if (participant.identity !== username) {
                        addMessage("SYSTEM", `${participant.identity} joined the chat`);
                    }
                });

                newRoom.on(RoomEvent.ParticipantDisconnected, (participant) => {
                    // console.log('Participant disconnected:', participant.identity);
                    if (participant.identity !== username) {
                        addMessage("SYSTEM", `${participant.identity} left the chat`);
                    }
                });

                const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;

                if (!livekitUrl) {
                    throw new Error('LiveKit URL not configured');
                }

                await newRoom.connect(livekitUrl, token);
                setRoom(newRoom);

            } catch (error) {
                console.error("Error Connecting to Room", error);
                setConnectionStatus("Connection Failed");
                addMessage("SYSTEM", "Failed to connect to chat room. Please refresh and try again.");
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

    const formatSenderName = (sender: string) => {
        if (sender === "SYSTEM") return "System";
        if (sender === "GEMINI") return "AI Assistant";
        if (sender === username) return "You";
        return sender;
    };

    const getSenderColor = (sender: string) => {
        if (sender === "SYSTEM") return "bg-gray-600";
        if (sender === "GEMINI") return "bg-green-600";
        if (sender === username) return "bg-blue-500";
        return "bg-purple-500";
    };

    return (
        <div className="flex flex-col h-screen bg-black text-white max-w-screen mx-auto">
            {/* Header */}
            <div className="p-3 sm:p-4 border-b border-gray-800 text-center text-base sm:text-lg font-semibold sticky top-0 bg-black">
                {username}&apos;s Chat with AI Assistant
                <div className={`text-xs mt-1 ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                    {connectionStatus}
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3 sm:space-y-4">
                {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-500 text-sm sm:text-base">
                        Waiting for connection... Once connected, start chatting with the AI!
                    </div>
                ) : (
                    messages.map((msg, index) => (
                        <div key={index} className={`flex ${msg.sender === username ? "justify-end" : "justify-start"}`}>
                            <div className="flex flex-col max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg">
                                <div className="text-xs text-gray-400 mb-1 px-2">
                                    {formatSenderName(msg.sender)} • {msg.timestamp.toLocaleTimeString()}
                                </div>
                                <div className={`rounded-2xl px-3 sm:px-4 py-2 text-sm sm:text-base ${getSenderColor(msg.sender)} text-white`}>
                                    {msg.text}
                                </div>
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
                    placeholder={isConnected ? "Message AI Assistant..." : "Connecting..."}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    className="flex-1 px-3 sm:px-4 py-2 rounded-full bg-gray-900 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus-visible:ring-blue-500 text-sm sm:text-base"
                    disabled={!isConnected}
                />
                <Button
                    onClick={handleSendMessage}
                    className="p-2 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    disabled={!isConnected || !message.trim()}
                >
                    <Send className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </Button>
            </div>
        </div>
    );
};

export default ChatPage;