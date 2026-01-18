from __future__ import annotations

from enum import Enum


class PluginType(str, Enum):
    solver = "solver"
    physics = "physics"
    ml = "ml"
    loss = "loss"
    inverse = "inverse"
    uq = "uq"
    io = "io"
    report = "report"


# Selection tiers (registry ranking)
QUALITY_ORDER = {
    "experimental": 0,
    "stable": 1,
    "certified": 2,
}

# pip entrypoints group name
DEFAULT_ENTRYPOINT_GROUP = "upi.plugins"

# Default monorepo scan roots (relative to repo root)
DEFAULT_FS_PLUGIN_DIRS = [
    "plugins",          # upi_adf/plugins/...
    "packages/plugins", # upi_adf/packages/plugins/...
]

# Central enablelist file names at repo root
ENABLELIST_FILENAMES = ["_enabled.yml", "_enabled.yaml"]

# Default run directory name (under repo root unless overridden)
DEFAULT_RUNS_DIRNAME = "runs"
