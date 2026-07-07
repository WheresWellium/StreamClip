import { ApiClientError, jobsApi } from "@/lib/api/client";
import {
  getClientAccessToken,
  getClientDeviceId,
} from "@/lib/auth/client-session";

export type ApprovalActionState = {
  status: "idle" | "ok" | "error";
  message?: string;
  approval_status?: string;
};

export async function updateClipApprovalAction(
  jobId: string,
  clipId: string,
  approval_status: "draft" | "approved" | "rejected",
): Promise<ApprovalActionState> {
  const token = getClientAccessToken();
  const deviceId = getClientDeviceId();
  try {
    const result = await jobsApi.updateClipApproval(
      jobId,
      clipId,
      approval_status,
      token ?? undefined,
      deviceId ?? undefined,
    );
    return { status: "ok", approval_status: result.approval_status };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not update approval." };
  }
}
