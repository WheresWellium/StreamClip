import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiClientError } from "@/lib/api/client";
import {
  ACCESS_TOKEN_COOKIE,
  DEVICE_ID_COOKIE,
  REFRESH_TOKEN_COOKIE,
  authHeaders,
} from "@/lib/auth/session";

const API_BASE = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const jar = await cookies();
  const token = jar.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!token) {
    return Response.json({ message: "Authentication required" }, { status: 401 });
  }

  let body: { device_id?: string };
  try {
    body = await request.json();
  } catch {
    return Response.json({ message: "Invalid body" }, { status: 400 });
  }

  const deviceId = body.device_id ?? jar.get(DEVICE_ID_COOKIE)?.value;
  if (!deviceId) {
    return Response.json({ message: "Device ID required" }, { status: 400 });
  }

  const res = await fetch(`${API_BASE}/api/auth/claim-device`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token, deviceId),
    },
    body: JSON.stringify({ device_id: deviceId }),
    cache: "no-store",
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    return Response.json(
      { message: payload.message ?? "Claim failed" },
      { status: res.status },
    );
  }

  return Response.json(await res.json());
}
