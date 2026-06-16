import { NextResponse } from "next/server";
import { fetchBotApi, ApiStats } from "@/lib/api";

export async function GET() {
  try {
    const data = await fetchBotApi<ApiStats>("/api/stats");
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
