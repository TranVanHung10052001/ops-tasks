import { NextRequest, NextResponse } from "next/server";
import { fetchBotApi, ApiPerformanceTeam } from "@/lib/api";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const days = searchParams.get("days") ?? "30";
  const userId = searchParams.get("user_id");
  const qs = new URLSearchParams({ days });
  if (userId) qs.set("user_id", userId);
  try {
    const data = await fetchBotApi<ApiPerformanceTeam>(`/api/performance?${qs.toString()}`);
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
