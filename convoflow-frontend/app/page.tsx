"use client"

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useRouter } from "next/navigation";


export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");

  const handleJoinRoom = () => {
    router.push(`/chat/${username}`)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleJoinRoom();
    }
  }

  return (
    <div className="min-w-screen min-h-screen bg-black items-center justify-center flex">
      <div className="flex flex-col min-w-[50%] min-h-[50%] items-center">
        <h1 className="text-white">Join A Room to Access Agent</h1>
        <div className="flex flex-col gap-4 mt-10 border rounded-xl border-white p-4 w-full h-full">
          <Label className="text-gray-200">Username</Label>
          <Input
            type="text"
            value={username}
            onKeyDown={handleKeyPress}
            placeholder="Enter an Username"
            className="focus-visible:ring-green-300 text-white"
            onChange={(e) => setUsername(e.target.value)}
          />
          <Button
            className="bg-blue-600 hover:bg-blue-800"
            onClick={() => { handleJoinRoom() }}>
            Join Room
          </Button>
        </div>
      </div>
    </div>
  );
}
