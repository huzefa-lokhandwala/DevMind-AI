"use client";

import { useEffect, useState } from "react";
import { checkReadiness } from "@/lib/api-client";
import { Activity, WifiOff } from "lucide-react";

export type ConnectionState = "CONNECTED" | "CONNECTING" | "DISCONNECTED";

export function StatusBadge() {
  const [state, setState] = useState<ConnectionState>("CONNECTING");
  const [dbStatus, setDbStatus] = useState<string>("");

  useEffect(() => {
    let isMounted = true;

    async function pollStatus() {
      try {
        const res = await checkReadiness();
        if (isMounted) {
          if (res.status === "ready") {
            setState("CONNECTED");
            setDbStatus(res.database);
          } else {
            setState("DISCONNECTED");
          }
        }
      } catch {
        if (isMounted) {
          setState("DISCONNECTED");
        }
      }
    }

    pollStatus();
    // Poll every 15 seconds
    const interval = setInterval(pollStatus, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex items-center space-x-2 text-xs font-mono px-2.5 py-1 rounded-full border border-zinc-800 bg-zinc-900/80 backdrop-blur-sm">
      {state === "CONNECTED" && (
        <>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-emerald-400 font-semibold tracking-wider">CONNECTED</span>
          {dbStatus === "connected" && (
            <span className="text-zinc-500 hidden sm:inline">(pgvector)</span>
          )}
        </>
      )}

      {state === "CONNECTING" && (
        <>
          <Activity className="w-3 h-3 text-amber-400 animate-spin" />
          <span className="text-amber-400 font-semibold tracking-wider">CONNECTING</span>
        </>
      )}

      {state === "DISCONNECTED" && (
        <>
          <WifiOff className="w-3 h-3 text-rose-400" />
          <span className="text-rose-400 font-semibold tracking-wider">OFFLINE</span>
        </>
      )}
    </div>
  );
}
