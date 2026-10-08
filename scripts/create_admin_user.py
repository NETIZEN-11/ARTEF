#!/usr/bin/env python3
"""Create admin user for ARTEF platform."""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import get_password_hash
from app.models.user import Base, User


async def create_admin_user():
    """Create the default admin user."""
    database_url = "sqlite+aiosqlite:///backend/redteam_dev.db"
    
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("âœ“ Admin user already exists")
            return
        
        admin_user = User(
            id=str(uuid4()),
            email="admin@redteam.local",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            is_active=True,
            is_superuser=True,
        )
        
        session.add(admin_user)
        await session.commit()
        
        print("âœ“ Admin user created successfully!")
        print("  Username: admin")
        print("  Password: admin123")
        print("  Email: admin@redteam.local")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
