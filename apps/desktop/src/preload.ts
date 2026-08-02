import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("streamclip", {
  version: () => ipcRenderer.invoke("streamclip:version") as Promise<string>,
  sidecar: {
    start: () => ipcRenderer.invoke("streamclip:sidecar-start") as Promise<{ started: boolean }>,
    stop: () => ipcRenderer.invoke("streamclip:sidecar-stop") as Promise<{ stopped: boolean }>,
    restart: () =>
      ipcRenderer.invoke("streamclip:sidecar-restart") as Promise<{ restarted: boolean }>,
    health: () =>
      ipcRenderer.invoke("streamclip:sidecar-health") as Promise<{
        healthy: boolean;
        url: string;
      }>,
    openLog: () => ipcRenderer.invoke("streamclip:sidecar-open-log") as Promise<{ opened: boolean }>,
  },
});
