"""Database ORM model package, provides Tortoise ORM model definitions and database lifecycle management modules."""

from core.database.connect import get_db_config  # Get database config dict for Tortoise ORM migration/init

# TORTOISE_ORM config constant required by Aerich migration tool for auto-discovering models and connection info.
TORTOISE_ORM = get_db_config()

