# ORM - object relational mapping
# this file handle database connection 

from collections.abc import AsyncGenerator
import uuid
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable  
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from datetime import datetime, timezone


DATABASE_URL = "postgresql+asyncpg://postgres:none@localhost/fastapi_db"


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTable[uuid.UUID], Base):
    __tablename__ = "user"  
    

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    title = Column(String(255), nullable=True)           
    content = Column(Text, nullable=True)                
    url = Column(String(500), nullable=False)            
    file_type = Column(String(50), nullable=False)       
    file_name = Column(String(255), nullable=False)      
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="posts")


engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn: 
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session