"""
UPI Core - Unified Plugin Infrastructure (control plane).

Public usage:
    import upi_core as upi
    upi.run("pipeline.yml")
"""

from .version import __version__, API_LEVEL

# Public API facade
from .api.public import (
    load_pipeline,
    scan_plugins,
    list_plugins,
    validate,
    explain,
    run,
    doctor,
)

__all__ = [
    "__version__",
    "API_LEVEL",
    "load_pipeline",
    "scan_plugins",
    "list_plugins",
    "validate",
    "explain",
    "run",
    "doctor",
]
