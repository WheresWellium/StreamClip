import { cookies } from "next/headers";

const API_BASE = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const jar = await cookies();
  const token = jar.get("streamclip_access_token")?.value;

  const headers: Record<string, string> = {
    Accept: "text/event-stream",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const lastEventId = request.headers.get("Last-Event-Id");
  if (lastEventId) headers["Last-Event-Id"] = lastEventId;

  const upstream = await fetch(
    `${API_BASE}/api/distribution/publish-jobs/${id}/progress`,
    { headers, cache: "no-store" },
  );

  if (!upstream.ok || !upstream.body) {
    return new Response(
      JSON.stringify({ message: "Publish progress stream unavailable" }),
      { status: upstream.status || 502, headers: { "Content-Type": "application/json" } },
    );
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
