"""Imports every domain's models so Alembic autogenerate and tests see them.

Add an import HERE whenever you create a new domain model —
otherwise Alembic will not detect its table.
"""

from app.users.models import User

__all__ = ["User"]
