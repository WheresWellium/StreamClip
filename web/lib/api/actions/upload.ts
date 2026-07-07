import { uploadsApi } from "@/lib/api/client";
import type { UploadInitRequest, UploadInitResponse } from "@/lib/api/types";
import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";

export async function initUploadAction(
  body: UploadInitRequest,
): Promise<UploadInitResponse> {
  const token = getClientAccessToken();
  const deviceId = getClientDeviceId();
  return uploadsApi.init(body, token, deviceId);
}
