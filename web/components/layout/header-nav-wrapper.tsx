import { getAccessToken } from "@/lib/auth/session";
import { HeaderNav } from "./header-nav";

export async function HeaderNavWrapper() {
  const token = await getAccessToken();
  return <HeaderNav isAuthenticated={!!token} />;
}
