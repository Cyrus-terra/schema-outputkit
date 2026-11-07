"""Expose the shared Hermes adapter to hosts that discover root manifests."""

import runpy
from pathlib import Path

register = runpy.run_path(
    str(Path(__file__).resolve().parent / ".hermes-plugin/__init__.py")
)["register"]
