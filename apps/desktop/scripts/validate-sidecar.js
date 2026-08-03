// electron-builder afterPack hook.
//
// Refuses to produce an installer that is missing the packaged sidecar engine.
// The recurring failure mode is a "successful" build whose extraResources were
// stale/empty (e.g. `-SkipSidecar` after a UI change, or building the mac/linux
// target on a host that never staged a sidecar) — the app then white-screens on
// launch because nothing listens on the health port. Catching it here turns a
// silent broken release into a hard build failure.
//
// Lives under apps/desktop/scripts/ (not build/) so git tracks it — root
// .gitignore ignores build/.

const fs = require("fs");
const path = require("path");

/** Depth-first search for a file named `name` under `dir`. */
function findFile(dir, name) {
  if (!fs.existsSync(dir)) return null;
  const stack = [dir];
  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (entry.name === name) {
        return full;
      }
    }
  }
  return null;
}

exports.default = async function validateSidecar(context) {
  const { appOutDir, electronPlatformName, packager } = context;

  let resourcesDir;
  if (electronPlatformName === "darwin" || electronPlatformName === "mas") {
    const appName = packager.appInfo.productFilename;
    resourcesDir = path.join(appOutDir, `${appName}.app`, "Contents", "Resources");
  } else {
    resourcesDir = path.join(appOutDir, "resources");
  }

  const sidecarDir = path.join(resourcesDir, "sidecar");
  const binName =
    electronPlatformName === "win32" ? "streamclip-sidecar.exe" : "streamclip-sidecar";

  const found = findFile(sidecarDir, binName);
  if (!found) {
    throw new Error(
      `[validate-sidecar] Missing '${binName}' under ${sidecarDir}.\n` +
        `The packaged app has no runnable engine — it would white-screen on launch.\n` +
        `Stage the sidecar first via the platform build script:\n` +
        `  Windows: scripts\\build_desktop_installer.ps1\n` +
        `  macOS:   scripts/build_desktop_installer_macos.sh\n` +
        `Refusing to ship a broken installer.`,
    );
  }

  console.log(`[validate-sidecar] OK (${electronPlatformName}): ${found}`);
};
