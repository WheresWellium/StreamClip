"use client";

import { Upload, X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/form";
import { uploadsApi } from "@/lib/api/client";
import { formatBytes, cn } from "@/lib/utils/format";

interface DirectUploadProps {
  onUploaded: (storageKey: string, filename: string) => void;
  onCleared: () => void;
  currentKey: string | null;
}

/**
 * Client component that uploads a video file directly to MinIO via a
 * presigned PUT URL. The API never sees the bytes.
 *
 * Flow:
 *   1. User picks file → POST /api/uploads/init → returns presigned URL
 *   2. XHR PUT directly to MinIO (browser → storage, not via API)
 *   3. onUploaded(storage_key) fires; parent form references it on submit
 */
export function DirectUpload({
  onUploaded,
  onCleared,
  currentKey,
}: DirectUploadProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [progress, setProgress] = React.useState(0);
  const [status, setStatus] = React.useState<
    "idle" | "uploading" | "done" | "error"
  >("idle");
  const [error, setError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = async (f: File) => {
    setFile(f);
    setStatus("uploading");
    setProgress(0);
    setError(null);

    try {
      const storageKey = await uploadsApi.uploadFile(f, (pct) =>
        setProgress(pct),
      );
      setStatus("done");
      onUploaded(storageKey, f.name);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const handleClear = () => {
    setFile(null);
    setProgress(0);
    setStatus("idle");
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
    onCleared();
  };

  if (currentKey && status === "done") {
    return (
      <div className="flex items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-2 text-sm">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-2 w-2 rounded-full bg-green-500 shrink-0" />
          <span className="truncate text-foreground">{file?.name}</span>
          {file && (
            <span className="text-muted-foreground shrink-0">
              · {formatBytes(file.size)}
            </span>
          )}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={handleClear}
          aria-label="Remove file"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "relative rounded-md border-2 border-dashed border-border bg-secondary/20 transition-colors",
        status === "uploading" && "border-primary/40",
        status === "error" && "border-destructive/40",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/x-matroska"
        className="absolute inset-0 cursor-pointer opacity-0"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        disabled={status === "uploading"}
      />
      <div className="pointer-events-none flex flex-col items-center justify-center gap-2 px-4 py-8 text-center">
        <Upload className="h-6 w-6 text-muted-foreground" />
        {status === "uploading" && file ? (
          <div className="w-full max-w-xs space-y-2">
            <p className="text-sm font-medium truncate">{file.name}</p>
            <Progress value={progress} />
            <p className="text-xs text-muted-foreground">
              {(progress * 100).toFixed(0)}% — {formatBytes(file.size)}
            </p>
          </div>
        ) : status === "error" ? (
          <>
            <p className="text-sm font-medium text-destructive">
              Upload failed
            </p>
            <p className="text-xs text-muted-foreground">{error}</p>
          </>
        ) : (
          <>
            <p className="text-sm font-medium">Drop a video or click to browse</p>
            <p className="text-xs text-muted-foreground">
              MP4, MOV, MKV up to ~5 GB
            </p>
          </>
        )}
      </div>
    </div>
  );
}
