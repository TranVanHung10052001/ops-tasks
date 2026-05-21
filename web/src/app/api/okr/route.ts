import { NextResponse } from "next/server";
import { fetchBotApi, ApiOkrResponse } from "@/lib/api";

export async function GET() {
  try {
    const data = await fetchBotApi<ApiOkrResponse>("/api/okr");
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
