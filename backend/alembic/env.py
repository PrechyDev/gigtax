from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from core.config import settings
from db.base import Base  # imports every model so Base.metadata is fully populated

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the app's own settings for the DB URL instead of a static value in alembic.ini,
# so local/.env and deployed (Neon) environments both "just work".
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    # Keep the categories table in sync with db/seed_data/categories.json on every
    # migration run (dev or deploy) — categories.json is otherwise only ever applied by
    # hand, which is exactly how it drifted out of sync with the seed file after
    # categories were retired from it. Upsert-only (see scripts/seed_categories.py), so
    # this is safe to run unconditionally. Never invoked by the test suite, which builds
    # its tables via SQLAlchemy metadata directly rather than through Alembic.
    from scripts.seed_categories import seed_categories
    seed_categories()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
