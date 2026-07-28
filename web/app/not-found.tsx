import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center space-y-4">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-muted-foreground">
        This page doesn&apos;t exist or may have moved.
      </p>
      <Link href="/" className="text-sky-400 hover:underline text-sm">
        Back to home
      </Link>
    </div>
  );
}
