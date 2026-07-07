"use client";

import { useEffect, useState } from "react";

import { HeaderNav } from "./header-nav";
import { getClientAccessToken } from "@/lib/auth/client-session";

export function HeaderNavWrapper() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(Boolean(getClientAccessToken()));
    const onAuthChange = () => setIsAuthenticated(Boolean(getClientAccessToken()));
    window.addEventListener("storage", onAuthChange);
    window.addEventListener("focus", onAuthChange);
    window.addEventListener("auth-changed", onAuthChange);
    return () => {
      window.removeEventListener("storage", onAuthChange);
      window.removeEventListener("focus", onAuthChange);
      window.removeEventListener("auth-changed", onAuthChange);
    };
  }, []);

  return <HeaderNav isAuthenticated={isAuthenticated} />;
}
