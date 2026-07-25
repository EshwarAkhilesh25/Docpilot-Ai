"""Database migration verification module.

This module provides functionality to verify Alembic migration status
during application startup. It checks if the database schema is at the
latest migration and reports any pending migrations.
"""

import logging
import re
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MigrationVerificationError(Exception):
    """Exception raised when migration verification fails."""

    pass


class MigrationVerifier:
    """Verifies Alembic migration status."""

    def __init__(self, alembic_ini_path: str = "alembic.ini"):
        """Initialize the migration verifier.

        Args:
            alembic_ini_path: Path to the alembic.ini configuration file (unused, kept for API compatibility).
        """
        self._alembic_ini_path = alembic_ini_path
        self._versions_path = Path("alembic/versions")

    def _get_head_revision(self) -> str | None:
        """Get the head revision from migration files.

        Returns:
            The head revision identifier or None if not available.
        """
        try:
            if not self._versions_path.exists():
                pass
                return None

            # Find all migration files
            migration_files = list(self._versions_path.glob("*.py"))
            if not migration_files:
                pass
                return None

            # Extract revision numbers and find the latest
            revisions = []
            for file_path in migration_files:
                # Skip __pycache__ and non-migration files
                if file_path.name.startswith("__"):
                    continue

                # Read the file to extract revision
                content = file_path.read_text()
                # Match revision number in the format: revision = 'xxxxxxx'
                match = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", content)
                if match:
                    revision = match.group(1)
                    # Check if this is a head revision (down_revision is None or not present)
                    down_revision_match = re.search(
                        r"down_revision\s*=\s*['\"]([^'\"]+)['\"]", content
                    )
                    if not down_revision_match or down_revision_match.group(1) == "None":
                        revisions.append(revision)

            if not revisions:
                pass
                return None

            # Return the latest head revision (last in alphabetical order)
            return sorted(revisions)[-1]

        except Exception as e:
            pass
            raise MigrationVerificationError(f"Failed to get head revision: {e}")

    def get_current_revision(self) -> str | None:
        """Get the current database revision.

        This requires database connectivity. If the database is unreachable,
        it returns None.

        Returns:
            The current revision identifier or None if unavailable.
        """
        try:
            from sqlalchemy import create_engine, text

            # Create a synchronous engine for migration check with a 5-second timeout
            # Convert async URL to sync URL
            db_url = settings.DATABASE_URL.replace("+asyncpg", "")
            connect_args = {"connect_timeout": 5} if "postgresql" in db_url else {}
            engine = create_engine(db_url, connect_args=connect_args)

            with engine.connect() as connection:
                result = connection.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                current_rev = row[0] if row else None

            engine.dispose()
            return current_rev
        except Exception:
            pass
            return None

    def verify_migrations(self) -> dict:
        """Verify migration status.

        Returns:
            A dictionary with migration status information:
            - head_revision: The head revision identifier
            - current_revision: The current database revision
            - is_up_to_date: Whether the database is at the latest revision
            - has_pending_migrations: Whether there are pending migrations
            - error: Any error message if verification failed
        """
        result = {
            "head_revision": None,
            "current_revision": None,
            "is_up_to_date": False,
            "has_pending_migrations": True,
            "error": None,
        }

        try:
            head_rev = self._get_head_revision()
            result["head_revision"] = head_rev  # type: ignore

            if head_rev is None:
                result["error"] = "No migrations found - database may not be initialized"  # type: ignore
                return result

            current_rev = self.get_current_revision()
            result["current_revision"] = current_rev  # type: ignore

            if current_rev is None:
                result["error"] = "Database unreachable or not initialized"  # type: ignore
                result["has_pending_migrations"] = True
                return result

            result["is_up_to_date"] = current_rev == head_rev
            result["has_pending_migrations"] = current_rev != head_rev

            if result["has_pending_migrations"]:
                pass
            else:
                pass

        except Exception as e:
            result["error"] = str(e)  # type: ignore
            pass

        return result

    def log_migration_status(self) -> None:
        """Log migration status to structured logs."""
        self.verify_migrations()

        pass


def verify_database_migrations(alembic_ini_path: str = "alembic.ini") -> dict:
    """Verify database migrations and return status.

    This is a convenience function for migration verification.

    Args:
        alembic_ini_path: Path to the alembic.ini configuration file.

    Returns:
        A dictionary with migration status information.
    """
    verifier = MigrationVerifier(alembic_ini_path)
    return verifier.verify_migrations()
