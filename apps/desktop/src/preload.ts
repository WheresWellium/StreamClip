import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("streamclip", {
  version: "1.0.0",
});
