"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { LoadingScreen } from "../loading-screen";
import { useLoadingLifecycle } from "../hooks/use-loading-lifecycle";
import { resolveLoadingScreenConfig } from "../resolve-config";
import type { LoadingScreenConfigInput } from "../types";

interface LoadingScreenContextValue {
  /** Show the overlay for a feature/route load. */
  show: (config?: LoadingScreenConfigInput) => void;
  /** Mark the current load complete (respects min display + exit). */
  hide: () => void;
  /** Whether a programmatic overlay is active. */
  isActive: boolean;
}

const LoadingScreenContext = createContext<LoadingScreenContextValue | null>(
  null,
);

interface OverlaySession {
  id: number;
  config: LoadingScreenConfigInput;
}

interface FeatureLoadingOverlayProps {
  session: OverlaySession;
  exitRequested: boolean;
  onFinished: () => void;
}

function FeatureLoadingOverlay({
  session,
  exitRequested,
  onFinished,
}: FeatureLoadingOverlayProps) {
  const config = resolveLoadingScreenConfig(session.config);
  const lifecycle = useLoadingLifecycle({
    isReady: exitRequested,
    progressMode: config.progressMode,
    progress: config.progressMode === "determinate" ? config.progress : null,
    minDisplayMs: config.timing.minDisplayMs,
    entranceMs: config.timing.entranceMs,
    exitMs: config.timing.exitMs,
    maxWaitMs: config.timing.maxWaitMs,
    onLoadingComplete: config.onLoadingComplete,
    onTransitionComplete: () => {
      config.onTransitionComplete?.();
      onFinished();
    },
  });

  if (!lifecycle.showLoader) return null;

  return (
    <LoadingScreen
      config={session.config}
      phase={lifecycle.phase}
      progress={lifecycle.displayProgress}
      progressMode={
        config.progressMode === "determinate" ? "determinate" : "indeterminate"
      }
    />
  );
}

interface LoadingScreenProviderProps {
  children: ReactNode;
  /** Base config for programmatic overlays. */
  config?: LoadingScreenConfigInput;
}

/**
 * Optional app-level loading overlay for route/feature loads.
 * Does not replace the boot gate — use alongside SidecarReadyGate.
 * Guarantees a single overlay instance (no duplicates / races).
 */
export function LoadingScreenProvider({
  children,
  config: baseConfig,
}: LoadingScreenProviderProps) {
  const [session, setSession] = useState<OverlaySession | null>(null);
  const [exitRequested, setExitRequested] = useState(false);
  const nextId = useRef(0);

  const show = useCallback(
    (next?: LoadingScreenConfigInput) => {
      nextId.current += 1;
      setExitRequested(false);
      setSession({
        id: nextId.current,
        config: { ...baseConfig, ...next },
      });
    },
    [baseConfig],
  );

  const hide = useCallback(() => {
    setExitRequested(true);
  }, []);

  const onFinished = useCallback(() => {
    setSession(null);
    setExitRequested(false);
  }, []);

  const value = useMemo(
    () => ({
      show,
      hide,
      isActive: session != null,
    }),
    [show, hide, session],
  );

  return (
    <LoadingScreenContext.Provider value={value}>
      {children}
      {session ? (
        <FeatureLoadingOverlay
          key={session.id}
          session={session}
          exitRequested={exitRequested}
          onFinished={onFinished}
        />
      ) : null}
    </LoadingScreenContext.Provider>
  );
}

export function useLoadingScreen(): LoadingScreenContextValue {
  const ctx = useContext(LoadingScreenContext);
  if (!ctx) {
    throw new Error(
      "useLoadingScreen must be used within LoadingScreenProvider",
    );
  }
  return ctx;
}

/** Safe variant for optional provider presence. */
export function useLoadingScreenSafe(): LoadingScreenContextValue | null {
  return useContext(LoadingScreenContext);
}
