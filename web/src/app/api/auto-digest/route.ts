import { NextResponse } from "next/server";
import { fetchBotApi } from "@/lib/api";

export interface AutoDigestResponse {
  count: number;
  tasks: Array<{
    id: number;
    summary: string;
    assignee_id: number | null;
    assignee_name: string | null;
    priority: string;
    deadline: string | null;
    category: string;
    source: string;
    created_at: string;
  }>;
  ts: string;
}

export async function GET() {
  try {
    const data = await fetchBotApi<AutoDigestResponse>("/api/auto-digest");
    return NextResponse.json(data);
  } catch (err) {
    // No bot connected yet → return empty digest (not an error state for dashboard)
    return NextResponse.json({ count: 0, tasks: [], ts: new Date().toISOString() });
  }
}
