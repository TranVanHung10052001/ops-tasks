import { NextResponse } from "next/server";
import { fetchBotApi, ApiOkrResponse } from "@/lib/api";

export async function GET() {
  try {
    const data = await fetchBotApi<ApiOkrResponse>("/api/okr");
    return NextResponse.json(data);
  } catch {
    // Bot offline — return empty-but-valid shape so client-side guards work
    return NextResponse.json({
      objectives: [], actions: [], north_star: "", quarter: "Q2/2026",
      total_actions: 0, overdue_actions: 0, p0_actions: 0,
    } satisfies ApiOkrResponse);
  }
}
