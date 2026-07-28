import { app, BrowserWindow, Menu, Tray, nativeImage, ipcMain, shell } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import { autoUpdater } from "electron-updater";

const SIDECAR_HOST = process.env.STREAMCLIP_SIDECAR_HOST ?? "127.0.0.1";
const SIDECAR_PORT = Number(process.env.STREAMCLIP_SIDECAR_PORT ?? "8765");
const WEB_URL = process.env.STREAMCLIP_WEB_URL ?? `http://${SIDECAR_HOST}:${SIDECAR_PORT}/`;

const REPO_ROOT = path.resolve(__dirname, "../../..");
const isDev = !app.isPackaged;

let tray: Tray | null = null;
let mainWindow: BrowserWindow | null = null;
let sidecarProc: ChildProcess | null = null;

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
    if (await sidecarHealthy()) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function trayIcon(): Electron.NativeImage {
  const iconPath = path.join(__dirname, "../assets/tray-icon.png");
  const img = nativeImage.createFromPath(iconPath);
  if (!img.isEmpty()) return img;
  // 16×16 solid fallback when asset missing
  const dataUrl =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMElEQVQ4T2NkYGD4z0ABYBw1gGE0DBhGQ4NhNAwYRsOAYTQMGEbDgGE0DBhGwwBgNAwYRsOAYTQMgAEA0c0J8nQq8sQAAAAASUVORK5CYII=";
  return nativeImage.createFromDataURL(dataUrl);
}

function openWindow(): void {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
    mainWindow.focus();
    return;
  }
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  void (async () => {
    const win = mainWindow;
    if (!win || win.isDestroyed()) return;

    const healthy = await waitForSidecar();
    if (!healthy) {
      console.warn("Sidecar not healthy after wait — loading UI anyway (boot gate will retry)");
    }

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
      win.show();
      win.focus();
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
      label: "Start sidecar",
      click: () => {
        startSidecar();
      },
    },
    {
      label: "Stop sidecar",
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
  tray.setToolTip("qClip");
  tray.setContextMenu(buildMenu());
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

ipcMain.handle("streamclip:sidecar-health", async () => {
  const healthy = await sidecarHealthy();
  return { healthy, url: WEB_URL };
});

ipcMain.handle("streamclip:version", () => app.getVersion());

app.whenReady().then(() => {
  createTray();
  startSidecar();
  openWindow();

  autoUpdater.autoDownload = false;
  autoUpdater.on("update-available", () => {
    console.log("Update available — download via Check for updates or enable autoDownload");
  });
  if (!isDev && process.env.STREAMCLIP_AUTO_UPDATE !== "0") {
    void autoUpdater.checkForUpdatesAndNotify();
  }
});

app.on("window-all-closed", () => {
  // Tray app — keep running when the window is closed.
});

app.on("before-quit", () => {
  stopSidecar();
});
