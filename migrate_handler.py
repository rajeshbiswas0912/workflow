import os

from alembic import command
from alembic.config import Config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def handler(event, context):
    # 1. Create tables and stored procedures
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    command.upgrade(cfg, "head")

    # 2. Seed data (both seeders are safe to run repeatedly)
    from app.config.database import SessionLocal
    from app.seeders import admin_seeder
    from app.seeders.admin_permissions_seeder import seed_admin_permissions

    admin_seeder.main()
    with SessionLocal() as db:
        count = seed_admin_permissions(db)

    return {"status": "ok", "admin_permission_areas": count}
