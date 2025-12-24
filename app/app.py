from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from app.db import Post, AsyncSession, get_async_session, create_db_and_tables
from sqlalchemy import select
from contextlib import asynccontextmanager
from app.images import imagekit
import os
import tempfile
import shutil


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create database and tables"""
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(None),
    content: str = Form(None),
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
        
        # Upload to ImageKit (WITHOUT options - simpler!)
        file_handle = open(temp_file_path, "rb")
        
        print(f" Uploading file: {file.filename}")
        
        upload_result = imagekit.upload_file(
            file=file_handle,
            file_name=file.filename
        )
        
        print(f" Upload result type: {type(upload_result)}")
        print(f" Upload result: {upload_result}")
        
        # Handle both dict and object responses
        if isinstance(upload_result, dict):
            url = upload_result.get('url')
            name = upload_result.get('name') or file.filename
        else:
            url = getattr(upload_result, 'url', None)
            name = getattr(upload_result, 'name', file.filename)
        
        print(f" Extracted URL: {url}")
        print(f" Extracted name: {name}")
        
        # Check if upload was successful
        if not url:
            raise HTTPException(status_code=500, detail="File upload failed - no URL returned")
        
        # Determine file type
        file_type = "video" if file.content_type and file.content_type.startswith("video/") else "image"
        
        print(f" Saving to database...")
        
        # Save to database
        post = Post(
            title=title or "",
            content=content or "",
            url=url,
            file_type=file_type,
            file_name=name
        )
        
        print(f" Post object created: {type(post)}")
        
        session.add(post)
        await session.commit()
        
        print(f" Committed to database")
        
        # Refresh to get auto-generated fields
        try:
            await session.refresh(post)
            print(f" Refreshed post")
        except Exception as refresh_error:
            print(f" Refresh failed: {refresh_error}")
            # If refresh fails, manually query the post
            result = await session.execute(select(Post).where(Post.id == post.id))
            post = result.scalar_one()
        
        return {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat() if post.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f" Error occurred: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
    limit: int = 10,
    skip: int = 0,
    session: AsyncSession = Depends(get_async_session)
):
    """Get all posts from database"""
    result = await session.execute(
        select(Post)
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    
    posts_data = [
        {
            "id": str(post.id),
            "title": post.title,
            "content": post.content,
            "url": post.url,
            "file_type": post.file_type,
            "file_name": post.file_name,
            "created_at": post.created_at.isoformat() if post.created_at else None
        }
        for post in posts
    ]
    
    return {"posts": posts_data, "count": len(posts_data)}





# @app.get("/")
# def root():
#     """Health check endpoint"""
#     return {"status": "ok", "message": "FastAPI ImageKit Upload API"}



