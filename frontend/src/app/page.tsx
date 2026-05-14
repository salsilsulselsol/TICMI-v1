"use client";

import { useState } from "react";

export default function Home() {
  const [message, setMessage] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <h1 className="text-4xl font-bold mb-8">TICMI - Teach Me</h1>
        <p className="text-lg text-gray-600">
          Adaptive Digital Learning Platform for High School Mathematics
        </p>
      </div>

      <div className="mt-16 w-full max-w-2xl">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">
            Multi-Agent AI Learning System
          </h2>
          
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <span className="flex h-3 w-3 relative">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-3 w-3 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              </span>
              <span className="text-gray-600">
                {isConnected ? "Connected to AI Tutor" : "Disconnected"}
              </span>
            </div>

            <div className="border-t pt-4">
              <p className="text-gray-600 mb-4">
                The TICMI system uses a LangGraph multi-agent architecture with:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-600">
                <li><strong>Diagnostic Agent:</strong> Detects prerequisite knowledge gaps</li>
                <li><strong>Socratic Verification Agent:</strong> Asks probing questions using the Protege Effect</li>
                <li><strong>Dynamic Routing:</strong> Mix of LLM-driven and deterministic transitions</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
