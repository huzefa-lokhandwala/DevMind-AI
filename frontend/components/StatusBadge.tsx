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
    const interval = setInterval(pollStatus, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[#2A2A2A] bg-[#171717] text-xs font-mono">
      {state === "CONNECTED" && (
        <>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]"></span>
          </span>
          <span className="text-[#10B981] font-medium text-[11px] tracking-wide">Connected</span>
          {dbStatus === "connected" && (
            <span className="text-[#8c909f] text-[10px] hidden sm:inline">(pgvector)</span>
          )}
        </>
      )}

      {state === "CONNECTING" && (
        <>
          <Activity className="w-3 h-3 text-amber-400 animate-spin" />
          <span className="text-amber-400 font-medium text-[11px] tracking-wide">Connecting</span>
        </>
      )}

      {state === "DISCONNECTED" && (
        <>
          <WifiOff className="w-3 h-3 text-[#ffb4ab]" />
          <span className="text-[#ffb4ab] font-medium text-[11px] tracking-wide">Offline</span>
        </>
      )}
    </div>
  );
}
