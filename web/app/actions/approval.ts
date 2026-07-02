"use server";

import { revalidatePath } from "next/cache";

import { ApiClientError, jobsApi } from "@/lib/api/client";
import { getAccessToken, getDeviceId } from "@/lib/auth/session";

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
  const token = await getAccessToken();
  const deviceId = await getDeviceId();
  try {
    const result = await jobsApi.updateClipApproval(
      jobId,
      clipId,
      approval_status,
      token ?? undefined,
      deviceId ?? undefined,
    );
    revalidatePath(`/jobs/${jobId}`);
    revalidatePath("/");
    return { status: "ok", approval_status: result.approval_status };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { status: "error", message: err.message };
    }
    return { status: "error", message: "Could not update approval." };
  }
}
