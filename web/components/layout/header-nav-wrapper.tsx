"use client";

import { useEffect, useState } from "react";

import { HeaderNav } from "./header-nav";
import { getClientAccessToken } from "@/lib/auth/client-session";

export function HeaderNavWrapper() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(Boolean(getClientAccessToken()));
    const onStorage = () => setIsAuthenticated(Boolean(getClientAccessToken()));
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onStorage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onStorage);
    };
  }, []);

  return <HeaderNav isAuthenticated={isAuthenticated} />;
}
