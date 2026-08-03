import {
  app,
  BrowserWindow,
  Menu,
  Notification,
  Tray,
  nativeImage,
  ipcMain,
  shell,
} from "electron";
import { spawn, ChildProcess } from "child_process";
import { createWriteStream, existsSync, mkdirSync, readFileSync, WriteStream } from "fs";
import { createServer } from "net";
import path from "path";
import { autoUpdater } from "electron-updater";
import { extractFatalFromLog, failureReasonFor } from "./failure-reason";

const SIDECAR_HOST = process.env.STREAMCLIP_SIDECAR_HOST ?? "127.0.0.1";
const DEFAULT_SIDECAR_PORT = Number(process.env.STREAMCLIP_SIDECAR_PORT ?? "8765");
// The user pinned the endpoint if they set either var — never auto-relocate it.
const PORT_IS_EXPLICIT =
  process.env.STREAMCLIP_SIDECAR_PORT != null || process.env.STREAMCLIP_WEB_URL != null;

/** Hosted F13 collector on henna (secrets stay on Vercel; no SMTP in the exe). */
const DEFAULT_SUPPORT_COLLECTOR_URL =
  "https://streamclip-henna.vercel.app/api/support-ingest";

function resolveSupportCollectorUrl(): string | undefined {
  const fromEnv =
    process.env.OPS_WEBHOOK_URL?.trim() ||
    process.env.STREAMCLIP_SUPPORT_COLLECTOR_URL?.trim();
  if (fromEnv) return fromEnv;
  // Packaged builds forward to the hosted collector so Help → Report a bug /
  // Beta feedback leave the tester machine (local SQLite alone is not enough).
  if (app.isPackaged) return DEFAULT_SUPPORT_COLLECTOR_URL;
  return undefined;
}

// Resolved at startup: normally the default port, but relocated to a free port
// if 8765 is already held by an unrelated process (so we don't dead-end on the
// error page). Mutable because the chosen port is not known until app-ready.
let SIDECAR_PORT = DEFAULT_SIDECAR_PORT;
let WEB_URL = process.env.STREAMCLIP_WEB_URL ?? `http://${SIDECAR_HOST}:${SIDECAR_PORT}/`;

function webUrlForPort(port: number): string {
  return `http://${SIDECAR_HOST}:${port}/`;
}

/** True if we can bind host:port right now (i.e. it is free to use). */
function isPortFree(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const probe = createServer();
    probe.once("error", () => resolve(false));
    probe.once("listening", () => probe.close(() => resolve(true)));
    probe.listen(port, SIDECAR_HOST);
  });
}

/** Ask the OS for a free ephemeral port on the sidecar host. */
function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once("error", reject);
    probe.listen(0, SIDECAR_HOST, () => {
      const address = probe.address();
      if (address && typeof address === "object") {
        const { port } = address;
        probe.close(() => resolve(port));
      } else {
        probe.close(() => reject(new Error("could not resolve a free port")));
      }
    });
  });
}

/**
 * Decide which port the engine should use. Reuses a healthy leftover engine,
 * keeps the default when free, and only relocates when the default is occupied
 * by something else — never when the user pinned the endpoint.
 */
async function resolveSidecarPort(): Promise<void> {
  if (PORT_IS_EXPLICIT) return;
  if (await sidecarHealthy(600)) return; // healthy engine already on the default port
  if (await isPortFree(DEFAULT_SIDECAR_PORT)) return;
  try {
    const free = await findFreePort();
    SIDECAR_PORT = free;
    WEB_URL = webUrlForPort(free);
    console.warn(`Port ${DEFAULT_SIDECAR_PORT} is busy; using ${free} for the engine.`);
  } catch (err) {
    console.error("Free-port resolution failed; keeping default.", err);
  }
}

const REPO_ROOT = path.resolve(__dirname, "../../..");
const ASSETS_DIR = path.join(__dirname, "../assets");
const isDev = !app.isPackaged;

/** Health polling: tight early so a warm sidecar shows the UI almost instantly. */
const HEALTH_POLL_FAST_MS = 200;
const HEALTH_POLL_SLOW_MS = 750;
const HEALTH_FAST_WINDOW_MS = 10_000;
const SIDECAR_BOOT_TIMEOUT_MS = 180_000;

let tray: Tray | null = null;
let mainWindow: BrowserWindow | null = null;
let sidecarProc: ChildProcess | null = null;
let sidecarLog: WriteStream | null = null;
let sidecarExitInfo: { code: number | null; signal: string | null } | null = null;
let sidecarSpawnError: string | null = null;
let bootAnnounced = false;

function logFilePath(): string {
  const dir = app.getPath("logs");
  try {
    mkdirSync(dir, { recursive: true });
  } catch {
    /* logs dir is best-effort */
  }
  return path.join(dir, "sidecar.log");
}

/** Packaged macOS ships dual-arch sidecars under sidecar/{arm64,x64}/; legacy flat layout still works. */
function packagedSidecarDir(exeName: string): string {
  const base = path.join(process.resourcesPath, "sidecar");
  if (process.platform === "darwin") {
    const archDir = process.arch === "arm64" ? "arm64" : "x64";
    const nested = path.join(base, archDir);
    if (existsSync(path.join(nested, exeName))) {
      return nested;
    }
  }
  return base;
}

function sidecarCommand(): { cmd: string; args: string[]; cwd: string } {
  if (isDev) {
    return {
      cmd: process.platform === "win32" ? "python" : "python3",
      args: ["-m", "desktop_sidecar"],
      cwd: REPO_ROOT,
    };
  }
  const exeName = process.platform === "win32" ? "streamclip-sidecar.exe" : "streamclip-sidecar";
  const dir = packagedSidecarDir(exeName);
  const exePath = path.join(dir, exeName);
  return { cmd: exePath, args: [], cwd: dir };
}

function startSidecar(): void {
  if (sidecarProc) return;
  const { cmd, args, cwd } = sidecarCommand();

  if (!isDev && !existsSync(cmd)) {
    sidecarSpawnError = `Sidecar executable missing: ${cmd}`;
    console.error(sidecarSpawnError);
    return;
  }

  sidecarSpawnError = null;
  sidecarExitInfo = null;

  try {
    sidecarLog = createWriteStream(logFilePath(), { flags: "a" });
    sidecarLog.write(`\n=== sidecar start ${new Date().toISOString()} ===\n`);
  } catch {
    sidecarLog = null;
  }

  const supportCollector = resolveSupportCollectorUrl();
  sidecarProc = spawn(cmd, args, {
    cwd,
    env: {
      ...process.env,
      STREAMCLIP_SIDECAR_HOST: SIDECAR_HOST,
      STREAMCLIP_SIDECAR_PORT: String(SIDECAR_PORT),
      ...(supportCollector ? { OPS_WEBHOOK_URL: supportCollector } : {}),
    },
    stdio: sidecarLog ? ["ignore", "pipe", "pipe"] : "ignore",
    shell: false,
    windowsHide: true,
  });

  if (sidecarLog) {
    sidecarProc.stdout?.pipe(sidecarLog, { end: false });
    sidecarProc.stderr?.pipe(sidecarLog, { end: false });
  }

  // Without this listener Node turns a spawn failure into an uncaught exception.
  sidecarProc.on("error", (err) => {
    sidecarSpawnError = err.message;
    sidecarLog?.write(`spawn error: ${err.message}\n`);
    sidecarProc = null;
  });

  sidecarProc.on("exit", (code, signal) => {
    sidecarExitInfo = { code, signal };
    sidecarLog?.write(`sidecar exited code=${code} signal=${signal}\n`);
    sidecarProc = null;
  });
}

function stopSidecar(): void {
  if (!sidecarProc) return;
  sidecarProc.kill();
  sidecarProc = null;
}

/** Stop any live engine, then spawn a fresh one (error-page Retry/Restart). */
function restartSidecar(): void {
  stopSidecar();
  // Clear stale death evidence so waitForSidecar does not give up immediately.
  sidecarSpawnError = null;
  sidecarExitInfo = null;
  startSidecar();
}

function readFatalFromLog(): string | null {
  try {
    const text = readFileSync(logFilePath(), "utf8");
    // Tail only — FATAL is written near the end of a failed boot.
    const tail = text.length > 32_000 ? text.slice(-32_000) : text;
    return extractFatalFromLog(tail);
  } catch {
    return null;
  }
}

async function sidecarHealthy(timeoutMs = 1500): Promise<boolean> {
  try {
    const res = await fetch(`${WEB_URL}api/health`, {
      signal: AbortSignal.timeout(timeoutMs),
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForSidecar(maxMs = SIDECAR_BOOT_TIMEOUT_MS): Promise<boolean> {
  const started = Date.now();
  const deadline = started + maxMs;
  while (Date.now() < deadline) {
    if (await sidecarHealthy()) return true;
    // Give up early when the process died and cannot recover on its own.
    if (!sidecarProc && (sidecarSpawnError || sidecarExitInfo)) return false;
    const elapsed = Date.now() - started;
    const delay = elapsed < HEALTH_FAST_WINDOW_MS ? HEALTH_POLL_FAST_MS : HEALTH_POLL_SLOW_MS;
    await new Promise((r) => setTimeout(r, delay));
  }
  return false;
}

function appIcon(): Electron.NativeImage {
  for (const name of ["icon.png", "tray-icon.png"]) {
    const img = nativeImage.createFromPath(path.join(ASSETS_DIR, name));
    if (!img.isEmpty()) return img;
  }
  return nativeImage.createEmpty();
}

function trayIcon(): Electron.NativeImage {
  const icon = appIcon();
  if (icon.isEmpty()) return icon;
  return icon.resize({ width: 16, height: 16 });
}

function failureReason(): string {
  return failureReasonFor(sidecarSpawnError, sidecarExitInfo, readFatalFromLog());
}

async function showErrorPage(win: BrowserWindow): Promise<void> {
  const query = {
    reason: failureReason(),
    log: logFilePath(),
    url: WEB_URL,
  };
  try {
    await win.loadFile(path.join(ASSETS_DIR, "startup-error.html"), { query });
  } catch (err) {
    console.error("error page failed", err);
  }
}

function announceReady(): void {
  if (bootAnnounced || !Notification.isSupported()) return;
  bootAnnounced = true;
  try {
    new Notification({
      title: "qClip is running",
      body: "Ready in your system tray. Click the tray icon any time to reopen.",
      icon: appIcon().isEmpty() ? undefined : appIcon(),
    }).show();
  } catch {
    /* notifications are best-effort */
  }
}

function openWindow(): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    show: true,
    // Matches the app shell so there is never a white flash while chunks load.
    backgroundColor: "#0a0f1c",
    icon: appIcon().isEmpty() ? undefined : appIcon(),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      backgroundThrottling: false,
    },
  });

  // Paint a branded splash on the very first frame instead of blank white.
  void mainWindow.loadFile(path.join(ASSETS_DIR, "splash.html")).catch(() => undefined);

  void (async () => {
    const win = mainWindow;
    if (!win || win.isDestroyed()) return;

    const healthy = await waitForSidecar();
    if (win.isDestroyed()) return;

    if (!healthy) {
      await showErrorPage(win);
      return;
    }

    try {
      await win.loadURL(WEB_URL, { extraHeaders: "Cache-Control: no-cache\r\n" });
    } catch (err) {
      console.error("Initial load failed", err);
      await new Promise((r) => setTimeout(r, 1000));
      if (win.isDestroyed()) return;
      try {
        await win.loadURL(WEB_URL, { extraHeaders: "Cache-Control: no-cache\r\n" });
      } catch {
        await showErrorPage(win);
        return;
      }
    }

    if (!win.isDestroyed()) {
      win.focus();
      announceReady();
    }
  })();

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function buildMenu(): Menu {
  return Menu.buildFromTemplate([
    { label: "Open qClip", click: openWindow },
    { type: "separator" },
    {
      label: "Restart engine",
      click: () => {
        restartSidecar();
        // If the user is stuck on the error page, Retry-equivalent reload happens
        // when they click Retry/Restart there; tray restart brings the process up.
        if (mainWindow && !mainWindow.isDestroyed()) {
          void (async () => {
            const ok = await waitForSidecar(30_000);
            if (ok && !mainWindow?.isDestroyed()) {
              await mainWindow.loadURL(WEB_URL, {
                extraHeaders: "Cache-Control: no-cache\r\n",
              });
              announceReady();
            }
          })();
        }
      },
    },
    {
      label: "Open engine log",
      click: () => {
        void shell.openPath(logFilePath());
      },
    },
    { type: "separator" },
    { label: "Check for updates", click: () => void autoUpdater.checkForUpdatesAndNotify() },
    { type: "separator" },
    { label: "Quit qClip", click: () => app.quit() },
  ]);
}

function createTray(): void {
  if (tray) return;
  tray = new Tray(trayIcon());
  tray.setToolTip("qClip — starting…");
  tray.setContextMenu(buildMenu());
  tray.on("click", openWindow);
  tray.on("double-click", openWindow);
}

ipcMain.handle("streamclip:sidecar-start", async () => {
  startSidecar();
  return { started: true };
});

ipcMain.handle("streamclip:sidecar-stop", async () => {
  stopSidecar();
  return { stopped: true };
});

ipcMain.handle("streamclip:sidecar-restart", async () => {
  restartSidecar();
  return { restarted: true };
});

ipcMain.handle("streamclip:sidecar-health", async () => {
  const healthy = await sidecarHealthy();
  return { healthy, url: WEB_URL };
});

ipcMain.handle("streamclip:sidecar-open-log", async () => {
  const result = await shell.openPath(logFilePath());
  return { opened: result === "" };
});

ipcMain.handle("streamclip:version", () => app.getVersion());

// One tray icon, one engine, one window — a second launch focuses the first.
const gotSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    openWindow();
  });

  app.whenReady().then(async () => {
    createTray();

    // Pick a usable port before spawning so a busy 8765 doesn't dead-end.
    await resolveSidecarPort();

    // Reuse an already-healthy engine (e.g. left over from a previous session).
    if (!(await sidecarHealthy(800))) {
      startSidecar();
    }
    openWindow();

    void (async () => {
      const healthy = await waitForSidecar();
      tray?.setToolTip(healthy ? "qClip" : "qClip — engine not running");
    })();

    autoUpdater.autoDownload = false;
    autoUpdater.on("update-available", () => {
      console.log("Update available — download via Check for updates or enable autoDownload");
    });
    if (!isDev && process.env.STREAMCLIP_AUTO_UPDATE !== "0") {
      void autoUpdater.checkForUpdatesAndNotify();
    }
  });
}

app.on("window-all-closed", () => {
  // Tray app — keep running when the window is closed.
});

app.on("before-quit", () => {
  stopSidecar();
  sidecarLog?.end();
  sidecarLog = null;
});
