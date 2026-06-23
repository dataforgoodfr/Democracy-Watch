from logging.config import fileConfig
from os import getenv

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, pool

from alembic import context

load_dotenv()


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

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
    PG_USER = getenv("PG_USER")
    PG_PWD = getenv("PG_PWD")
    PG_DB = getenv("PG_DB")
    PG_HOST = getenv("PG_HOST", "localhost")
    PG_PORT = getenv("PG_PORT", "5432")
    PG_ECHO = getenv("PG_ECHO", False)
    pg_url = URL.create(
        drivername="postgresql+psycopg",
        username=PG_USER,
        password=PG_PWD,
        host=PG_HOST,
        port=int(PG_PORT),
        database=PG_DB,
    )
    connectable = create_engine(pg_url, poolclass=pool.NullPool, echo=bool(PG_ECHO))

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
