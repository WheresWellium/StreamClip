"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { useToastSafe } from "@/components/providers/toast-provider";

const PLATFORM_LABELS: Record<string, string> = {
  youtube_shorts: "YouTube Shorts",
  tiktok: "TikTok",
};

const ERROR_MESSAGES: Record<string, { title: string; description: string }> = {
  oauth_denied: {
    title: "Connection cancelled",
    description: "You declined platform authorization or the request was interrupted.",
  },
  oauth_failed: {
    title: "Connection failed",
    description: "Check OAuth app settings in Settings, then try again.",
  },
  unknown_platform: {
    title: "Unsupported platform",
    description: "This platform is not available on your install.",
  },
  pro_required: {
    title: "Pro required",
    description: "Activate a Pro license in Settings to connect platforms.",
  },
  distribution_not_configured: {
    title: "Server not configured",
    description: "DISTRIBUTION_TOKEN_KEY must be set on the API server.",
  },
  oauth_start_failed: {
    title: "Connect failed",
    description: "Configure your OAuth app in Settings first.",
  },
};

type Props = {
  connected?: string;
  error?: string;
};

export function DistributionOAuthToasts({ connected, error }: Props) {
  const router = useRouter();
  const { push: toast } = useToastSafe();
  const shown = React.useRef(false);

  React.useEffect(() => {
    if (shown.current || (!connected && !error)) return;
    shown.current = true;

    if (connected) {
      const label = PLATFORM_LABELS[connected] ?? connected;
      toast("Connected", `${label} is now linked to your account.`);
    } else if (error) {
      const msg = ERROR_MESSAGES[error] ?? {
        title: "Something went wrong",
        description: error.replace(/_/g, " "),
      };
      toast(msg.title, msg.description);
    }

    router.replace("/distribution");
  }, [connected, error, toast, router]);

  return null;
}
