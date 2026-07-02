import { app, BrowserWindow, Menu, Tray, nativeImage, shell } from "electron";
import { spawn, ChildProcess } from "child_process";
import path from "path";
import { autoUpdater } from "electron-updater";

const WEB_URL = process.env.STREAMCLIP_WEB_URL ?? "http://localhost:3000";
const COMPOSE_FILE = process.env.STREAMCLIP_COMPOSE_FILE ?? "docker-compose.prod.yml";
const REPO_ROOT = path.resolve(__dirname, "../../..");

let tray: Tray | null = null;
let composeProc: ChildProcess | null = null;

function runCompose(args: string[]): Promise<number> {
  return new Promise((resolve) => {
    const proc = spawn(
      "docker",
      ["compose", "-f", COMPOSE_FILE, ...args],
      { cwd: REPO_ROOT, shell: process.platform === "win32" },
    );
    proc.on("close", (code) => resolve(code ?? 1));
  });
}

async function startStack(): Promise<void> {
  if (composeProc) return;
  const code = await runCompose(["up", "-d"]);
  if (code !== 0) {
    console.error("docker compose up failed", code);
  }
}

async function stopStack(): Promise<void> {
  await runCompose(["down"]);
  composeProc = null;
}

function openBrowser(): void {
  void shell.openExternal(WEB_URL);
}

function buildMenu(): Menu {
  return Menu.buildFromTemplate([
    { label: "Open StreamClip", click: openBrowser },
    { type: "separator" },
    { label: "Start Docker stack", click: () => void startStack() },
    { label: "Stop Docker stack", click: () => void stopStack() },
    { type: "separator" },
    { label: "Check for updates", click: () => void autoUpdater.checkForUpdatesAndNotify() },
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ]);
}

function createTray(): void {
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip("StreamClip");
  tray.setContextMenu(buildMenu());
  tray.on("double-click", openBrowser);
}

app.whenReady().then(() => {
  createTray();
  void startStack();
  openBrowser();

  autoUpdater.autoDownload = false;
  autoUpdater.on("update-available", () => {
    console.log("Update available (stub — configure publish in electron-builder)");
  });
});

app.on("window-all-closed", (e: Event) => {
  e.preventDefault();
});

app.on("before-quit", () => {
  void stopStack();
});
