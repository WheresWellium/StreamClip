"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { templatesApi } from "@/lib/api/client";
import { getClientAccessToken } from "@/lib/auth/client-session";

export default function TemplatesSettingsPage() {
  const [token, setToken] = useState<string | undefined>();
  const [templates, setTemplates] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    const t = getClientAccessToken();
    setToken(t);
    if (!t) return;
    void templatesApi
      .list(t)
      .then((list) => setTemplates(list.map((x) => ({ id: x.id, name: x.name }))))
      .catch(() => setTemplates([]));
  }, []);

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <Link href="/settings" className="text-sm text-sky-400 hover:underline">
          ← Settings
        </Link>
        <h1 className="text-2xl font-semibold mt-2">Job templates</h1>
        <p className="text-muted-foreground text-sm">
          Saved clip settings for one-click job creation.
        </p>
      </div>

      {!token ? (
        <p className="text-sm text-muted-foreground">
          <Link href="/login" className="text-sky-400 hover:underline">Sign in</Link> to manage templates.
        </p>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Your templates</CardTitle>
            <CardDescription>{templates.length} saved</CardDescription>
          </CardHeader>
          <CardContent>
            {templates.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Save a template from the create-job form on the dashboard.
              </p>
            ) : (
              <ul className="divide-y divide-white/5">
                {templates.map((t) => (
                  <li key={t.id} className="py-2 text-sm">
                    {t.name}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
