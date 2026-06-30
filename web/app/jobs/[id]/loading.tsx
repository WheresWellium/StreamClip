import { ClipCardSkeleton } from "@/components/clips/clip-card";

export default function Loading() {
  return (
    <div className="space-y-6">
      <div className="h-4 w-24 skeleton rounded" />
      <div className="space-y-2">
        <div className="h-8 w-2/3 skeleton rounded" />
        <div className="h-4 w-1/3 skeleton rounded" />
      </div>
      <div className="h-24 skeleton rounded-lg" />
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <ClipCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
