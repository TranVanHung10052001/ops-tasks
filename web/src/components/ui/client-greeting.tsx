"use client";

import { useState, useEffect } from "react";
import { MEMBERS } from "@/lib/mock";

function timeGreeting(): string {
  const h = new Date().getHours();
  if (h >= 6 && h < 11) return "Chào sáng";
  if (h >= 11 && h < 14) return "Chào trưa";
  if (h >= 14 && h < 18) return "Chào chiều";
  if (h >= 18 && h < 22) return "Chào tối";
  return "Chào đêm";
}

export default function ClientGreeting() {
  const [uid, setUid] = useState("m0");

  useEffect(() => {
    setUid(localStorage.getItem("ops-uid") ?? "m0");
    const sync = () => setUid(localStorage.getItem("ops-uid") ?? "m0");
    window.addEventListener("ops-user-changed", sync);
    return () => window.removeEventListener("ops-user-changed", sync);
  }, []);

  const member = MEMBERS.find((m) => m.id === uid) ?? MEMBERS[0];
  const text = `${timeGreeting()}, ${member.name}`;

  return (
    <h1 className="text-[32px] text-text-primary editorial leading-tight">
      {text}.
    </h1>
  );
}
