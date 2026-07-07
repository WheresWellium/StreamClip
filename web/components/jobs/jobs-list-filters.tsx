"use client";

import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { Input, Select } from "@/components/ui/form";

export function JobsListFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = React.useState(searchParams.get("search") ?? "");
  const status = searchParams.get("status") ?? "";

  function apply(next: { search?: string; status?: string }) {
    const params = new URLSearchParams(searchParams.toString());
    if (next.search !== undefined) {
      if (next.search) params.set("search", next.search);
      else params.delete("search");
    }
    if (next.status !== undefined) {
      if (next.status) params.set("status", next.status);
      else params.delete("status");
    }
    router.push(`/jobs?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap gap-2 px-6 pb-3">
      <Input
        placeholder="Search title or URL…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && apply({ search })}
        className="max-w-xs h-8 text-sm"
      />
      <Select
        value={status}
        onChange={(e) => apply({ status: e.target.value })}
        className="h-8 text-sm w-36"
      >
        <option value="">All statuses</option>
        <option value="done">Done</option>
        <option value="processing">Processing</option>
        <option value="error">Error</option>
        <option value="queued">Queued</option>
      </Select>
    </div>
  );
}
