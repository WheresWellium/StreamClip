import { app, BrowserWindow, Menu, Tray, nativeImage, ipcMain, shell } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import { autoUpdater } from "electron-updater";

const SIDECAR_HOST = process.env.STREAMCLIP_SIDECAR_HOST ?? "127.0.0.1";
const SIDECAR_PORT = Number(process.env.STREAMCLIP_SIDECAR_PORT ?? "8765");
const WEB_URL = process.env.STREAMCLIP_WEB_URL ?? `http://${SIDECAR_HOST}:${SIDECAR_PORT}/`;

const REPO_ROOT = path.resolve(__dirname, "../../..");
const isDev = !app.isPackaged;

const PRODUCT_NAME = "qClip";

let tray: Tray | null = null;
let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let sidecarProc: ChildProcess | null = null;

type BootPhase = "spawn" | "splash" | "sidecar_start" | "sidecar_ready" | "first_paint" | "updater";

const bootMarks: Partial<Record<BootPhase, number>> = {};

function mark(phase: BootPhase): void {
  bootMarks[phase] = Date.now();
  const base = bootMarks.spawn ?? bootMarks[phase]!;
  console.log(`[boot] ${phase} +${bootMarks[phase]! - base}ms`);
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
  const exePath = path.join(process.resourcesPath, "sidecar", exeName);
  return { cmd: exePath, args: [], cwd: path.dirname(exePath) };
}

function startSidecar(): void {
  if (sidecarProc) return;
  mark("sidecar_start");
  const { cmd, args, cwd } = sidecarCommand();
  sidecarProc = spawn(cmd, args, {
    cwd,
    env: {
      ...process.env,
      STREAMCLIP_SIDECAR_HOST: SIDECAR_HOST,
      STREAMCLIP_SIDECAR_PORT: String(SIDECAR_PORT),
    },
    stdio: "ignore",
    shell: false,
  });
  sidecarProc.on("exit", (code) => {
    console.log("sidecar exited", code);
    sidecarProc = null;
  });
}

function stopSidecar(): void {
  if (!sidecarProc) return;
  sidecarProc.kill();
  sidecarProc = null;
}

async function sidecarHealthy(): Promise<boolean> {
  try {
    const res = await fetch(`${WEB_URL}api/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForSidecar(maxMs = 120_000): Promise<boolean> {
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    if (await sidecarHealthy()) {
      mark("sidecar_ready");
      return true;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return false;
}

function trayIcon(): Electron.NativeImage {
  const iconPath = path.join(__dirname, "../assets/tray-icon.png");
  const img = nativeImage.createFromPath(iconPath);
  if (!img.isEmpty()) return img;
  const dataUrl =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5n1bAAAAAASUVORK5CYII=";
  return nativeImage.createFromDataURL(dataUrl);
}

function splashPath(): string {
  return path.join(__dirname, "../assets/splash.html");
}

function setSplashPhase(label: string): void {
  if (!splashWindow || splashWindow.isDestroyed()) return;
  const safe = JSON.stringify(label);
  void splashWindow.webContents.executeJavaScript(
    `window.__qclipPhaseLocked=true;window.qclipSetPhase&&window.qclipSetPhase(${safe});`,
  );
}

function showSplash(): void {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.show();
    return;
  }
  mark("splash");
  splashWindow = new BrowserWindow({
    width: 420,
    height: 320,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    show: true,
    center: true,
    backgroundColor: "#0b1220",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  void splashWindow.loadFile(splashPath());
  splashWindow.on("closed", () => {
    splashWindow = null;
  });
}

function closeSplash(): void {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
  }
  splashWindow = null;
}

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    show: false,
    backgroundColor: "#0b1220",
    autoHideMenuBar: true,
    // Frameless chrome with native Windows caption buttons (min/max/close).
    titleBarStyle: "hidden",
    titleBarOverlay:
      process.platform === "darwin"
        ? undefined
        : {
            color: "#0b1220",
            symbolColor: "#e8eef7",
            height: 36,
          },
    trafficLightPosition: process.platform === "darwin" ? { x: 12, y: 12 } : undefined,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.setMenuBarVisibility(false);
  win.on("closed", () => {
    if (mainWindow === win) mainWindow = null;
  });
  return win;
}

async function openWindow(): Promise<void> {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
    return;
  }

  showSplash();
  setSplashPhase("Starting local engine");
  startSidecar();

  mainWindow = createMainWindow();
  const win = mainWindow;

  // Maximize (not exclusive fullscreen) so users keep resize + taskbar.
  win.maximize();

  const healthyPromise = waitForSidecar();
  setSplashPhase("Preparing your workspace");

  const healthy = await healthyPromise;
  if (!healthy) {
    console.warn("Sidecar not healthy after wait — loading UI anyway (boot gate will retry)");
  }

  setSplashPhase("Ready");

  try {
    await win.loadURL(WEB_URL, { extraHeaders: "Cache-Control: no-cache\r\n" });
  } catch (err) {
    console.error("Initial load failed", err);
    await new Promise((r) => setTimeout(r, 1500));
    if (!win.isDestroyed()) {
      await win.loadURL(WEB_URL, { extraHeaders: "Cache-Control: no-cache\r\n" });
    }
  }

  if (!win.isDestroyed()) {
    mark("first_paint");
    closeSplash();
    win.show();
    win.focus();
  }
}

function buildTrayMenu(): Menu {
  return Menu.buildFromTemplate([
    { label: `Open ${PRODUCT_NAME}`, click: () => void openWindow() },
    { type: "separator" },
    {
      label: "Start local engine",
      click: () => {
        startSidecar();
      },
    },
    {
      label: "Stop local engine",
      click: () => {
        stopSidecar();
      },
    },
    { type: "separator" },
    { label: "Check for updates", click: () => void autoUpdater.checkForUpdatesAndNotify() },
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ]);
}

function createTray(): void {
  tray = new Tray(trayIcon());
  tray.setToolTip(PRODUCT_NAME);
  tray.setContextMenu(buildTrayMenu());
  tray.on("double-click", () => void openWindow());
}

function scheduleUpdater(): void {
  autoUpdater.autoDownload = false;
  autoUpdater.on("update-available", () => {
    console.log("Update available — download via Check for updates or enable autoDownload");
  });
  if (!isDev && process.env.STREAMCLIP_AUTO_UPDATE !== "0") {
    // Defer until after first paint so updater does not compete with boot I/O.
    setTimeout(() => {
      mark("updater");
      void autoUpdater.checkForUpdatesAndNotify();
    }, 8_000);
  }
}

ipcMain.handle("streamclip:sidecar-start", async () => {
  startSidecar();
  return { started: true };
});

ipcMain.handle("streamclip:sidecar-stop", async () => {
  stopSidecar();
  return { stopped: true };
});

ipcMain.handle("streamclip:sidecar-health", async () => {
  const healthy = await sidecarHealthy();
  return { healthy, url: WEB_URL };
});

ipcMain.handle("streamclip:version", () => app.getVersion());

ipcMain.handle("streamclip:boot-timings", () => ({ ...bootMarks }));

app.whenReady().then(() => {
  mark("spawn");
  // Remove File/Edit/View/Window/Help — tray + OS caption buttons are enough.
  Menu.setApplicationMenu(null);
  createTray();
  void openWindow().then(() => scheduleUpdater());
});

app.on("window-all-closed", () => {
  // Tray app — keep running when the window is closed.
});

app.on("before-quit", () => {
  closeSplash();
  stopSidecar();
});
