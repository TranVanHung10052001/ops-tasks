import { NextResponse } from "next/server";
import { fetchBotApi, ApiMember } from "@/lib/api";

export async function GET() {
  try {
    const data = await fetchBotApi<ApiMember[]>("/api/team");
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
