"use server";

import { cookies } from "next/headers";

import { ApiClientError } from "@/lib/api/client";
import type { UploadInitRequest, UploadInitResponse } from "@/lib/api/types";
import {
  ACCESS_TOKEN_COOKIE,
  DEVICE_ID_COOKIE,
  authHeaders,
} from "@/lib/auth/session";

const API_BASE = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function initUploadAction(
  body: UploadInitRequest,
): Promise<UploadInitResponse> {
  const jar = await cookies();
  const token = jar.get(ACCESS_TOKEN_COOKIE)?.value;
  const deviceId = jar.get(DEVICE_ID_COOKIE)?.value;

  const res = await fetch(`${API_BASE}/api/uploads/init`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(token, deviceId),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new ApiClientError(
      res.status,
      payload.code ?? `http_${res.status}`,
      payload.message ?? res.statusText,
      payload,
    );
  }

  return (await res.json()) as UploadInitResponse;
}
