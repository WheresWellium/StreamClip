import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("streamclip", {
  version: () => ipcRenderer.invoke("streamclip:version") as Promise<string>,
  bootTimings: () =>
    ipcRenderer.invoke("streamclip:boot-timings") as Promise<Record<string, number>>,
  sidecar: {
    start: () => ipcRenderer.invoke("streamclip:sidecar-start") as Promise<{ started: boolean }>,
    stop: () => ipcRenderer.invoke("streamclip:sidecar-stop") as Promise<{ stopped: boolean }>,
    health: () =>
      ipcRenderer.invoke("streamclip:sidecar-health") as Promise<{
        healthy: boolean;
        url: string;
      }>,
  },
});
