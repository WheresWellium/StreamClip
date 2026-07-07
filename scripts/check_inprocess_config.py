"""Assert queue.backend=inprocess — used by scripts/verify_inprocess.ps1."""
from core.config import get_settings

cfg = get_settings(reload=True)
assert cfg.queue.backend == "inprocess", cfg.queue.backend
print("queue.backend=", cfg.queue.backend)
