from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from app.db import Post, AsyncSession, get_async_session, create_db_and_tables, User
from sqlalchemy import select
from contextlib import asynccontextmanager
from app.images import imagekit
import os
import tempfile
import shutil
from app.users import auth_backend, fastapi_users, current_active_user
from app.schema import UserRead, UserCreate, UserUpdate  # 👈 Added UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create database and tables"""
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

# ============ AUTH ROUTES ============
app.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/auth/jwt", 
    tags=["auth"]
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate), 
    prefix="/auth", 
    tags=["auth"]
)

app.include_router(
    fastapi_users.get_reset_password_router(), 
    prefix="/auth", 
    tags=["auth"]
)

app.include_router(
    fastapi_users.get_verify_router(UserRead), 
    prefix="/auth", 
    tags=["auth"]
)

# ============ USER ROUTES (only register ONCE!) ============
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),  # 👈 FIXED: Correct order & only once
    prefix="/users", 
    tags=["users"]
)


# ============ POST ROUTES ============

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(None),
    content: str = Form(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upload file to ImageKit and save metadata to database"""
    temp_file_path = None
    file_handle = None
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)
        
        # Upload to ImageKit
        file_handle = open(temp_file_path, "rb")
        upload_result = imagekit.upload_file(
            file=file_handle,
            file_name=file.filename
        )
        
        # Handle both dict and object responses
        if isinstance(upload_result, dict):
            url = upload_result.get('url')
            name = upload_result.get('name') or file.filename
        else:
            url = getattr(upload_result, 'url', None)
            name = getattr(upload_result, 'name', file.filename)
        
        # Check if upload was successful
        if not url:
            raise HTTPException(status_code=500, detail="File upload failed - no URL returned")
        
        # Determine file type
        file_type = "video" if file.content_type and file.content_type.startswith("video/") else "image"
        
        # Save to database
        post = Post(
            title=title or "",
            content=content or "",
            url=url,
            file_type=file_type,
            file_name=name,
            user_id=user.id  # 👈 FIXED: Changed User.id to user.id
        )
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        return {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "user_id": str(post.user_id),
            "created_at": post.created_at.isoformat() if post.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    finally:
        # Cleanup
        if file_handle:
            file_handle.close()
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


@app.get("/feed")
async def get_feed(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get all posts from database"""
    # Get posts
    result = await session.execute(
        select(Post).order_by(Post.created_at.desc())
    )
    posts = result.scalars().all()
    
    # Get users (more efficient)
    result = await session.execute(select(User))
    users = result.scalars().all()
    user_dict = {str(u.id): u.email for u in users}
    
    # Build response
    posts_data = [
        {
            "id": str(post.id),
            "user_id": str(post.user_id),  
            "title": post.title,
            "content": post.content,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "is_owner": post.user_id == user.id,
            "email": user_dict.get(str(post.user_id), "Unknown")
        }
        for post in posts
    ]
    
    return {"posts": posts_data, "count": len(posts_data)}


@app.delete("/post/{post_id}")
async def delete_post(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a post by ID"""
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if user.id != post.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    await session.delete(post)
    await session.commit()
    
    return {"detail": "Post deleted successfully"}


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "FastAPI ImageKit Upload API"}



