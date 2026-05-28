import { NextRequest, NextResponse } from "next/server";
import { fetchBotApi } from "@/lib/api";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    if (!body?.question || typeof body.question !== "string") {
      return NextResponse.json({ error: "question is required" }, { status: 400 });
    }
    const data = await fetchBotApi<{
      answer: string;
      tools_used: string[];
      tool_results: Record<string, unknown>;
    }>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question: body.question }),
    });
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json(
      { error: String(err), answer: "Bot offline — start bot/server.py để dùng AI Ask." },
      { status: 502 },
    );
  }
}
