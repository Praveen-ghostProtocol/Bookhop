"""Local development.

Default engine here is SQLite, because the founder's Windows machine has
neither PostgreSQL nor Docker installed and a slice that cannot be run is not a
slice. Point it at the production engine with BOOKHOP_DB_ENGINE=postgres once
Postgres exists locally; nothing else changes.

READ company/architecture/ENGINE-DIVERGENCE.md. Some correctness properties of
this schema are NOT verified by a green test run on SQLite.
"""

import os

os.environ.setdefault("BOOKHOP_DB_ENGINE", "sqlite")

from .base import *  # noqa: E402,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
