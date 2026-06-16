import { NextRequest, NextResponse } from "next/server";

const BOT_URL    = process.env.NEXT_PUBLIC_API_URL    ?? "http://localhost:8000";
const BOT_SECRET = process.env.NEXT_PUBLIC_API_SECRET ?? "ops-tasks-secret-change-me";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body?.question || typeof body.question !== "string") {
      return NextResponse.json({ error: "question is required" }, { status: 400 });
    }

    const res = await fetch(`${BOT_URL}/api/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${BOT_SECRET}`,
      },
      body: JSON.stringify({ question: body.question }),
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text();
      return NextResponse.json(
        { error: text, answer: "Bot offline — start bot/server.py để dùng AI Ask." },
        { status: 502 },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: String(err), answer: "Bot offline — start bot/server.py để dùng AI Ask." },
      { status: 502 },
    );
  }
}
