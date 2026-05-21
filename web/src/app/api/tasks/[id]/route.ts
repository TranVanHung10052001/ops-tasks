import { NextRequest, NextResponse } from "next/server";
import { fetchBotApi } from "@/lib/api";

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const body = await req.json();
    const data = await fetchBotApi(`/api/tasks/${params.id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
