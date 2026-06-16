import { NextRequest, NextResponse } from "next/server";
import { fetchBotApi } from "@/lib/api";

export async function GET() {
  try {
    const data = await fetchBotApi<Record<string, string>>("/api/metrics");
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({}, { status: 200 }); // Return empty (not 502) — no metrics yet is normal
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const data = await fetchBotApi("/api/metrics/bulk", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
