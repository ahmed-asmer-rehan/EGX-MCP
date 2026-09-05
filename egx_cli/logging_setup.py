"""
Silence Domain/ and tvDatafeed's logging noise by default (Constitution Principle IV --
verbose/debug output is opt-in only). Domain/egx_controller.py and Domain/download.py each
call logging.basicConfig(level=INFO) and logger.setLevel(DEBUG) at import time, and tvDatafeed
logs its own warnings (rate-limit retries, "nologin" notices) -- none of that is ours to
reconfigure per-logger. logging.disable() is a single global gate that overrides every
logger's own level regardless of name or when it was configured, so it's the one mechanism
that reliably silences all of it without touching Domain/ or tvDatafeed at all.
"""

import logging


def configure(verbose: bool) -> None:
    logging.disable(logging.NOTSET if verbose else logging.CRITICAL)
