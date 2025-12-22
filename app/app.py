from fastapi import FastAPI , HTTPException
from .schema import postCreate , postresponse
from app.db import Post,AsyncSession,get_async_session,  create_db_and_tables


from sqlalchemy.ext.asyncio import AsyncSession

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database and tables
    await create_db_and_tables()
    yield
    # Shutdown: any cleanup can be done here if needed
    

app = FastAPI(lifespan=lifespan)

@app.get("/hello-world")
def hellow_world():
    return {"message": "Hello, World!"}

text_posts ={1: {"title": "First Post", "content": "This is the content of the first post"},
             2: {"title":  "Second Post", "content": "This is the content of the second post"},
             3: {"title":  "Third Post", "content": "This is the content of the third post"},
                4: {"title":  "Fourth Post", "content": "This is the content of the fourth post"},
                5: {"title":  "Fifth Post", "content": "This is the content of the fifth post"},
                6: {"title":  "Sixth Post", "content": "This is the content of the sixth post"},
                }
# ============ GET Methods ============

# GET all posts (with optional limit)
@app.get("/posts")
def get_all_posts(limit: int = None) -> list[postresponse]:
    """Get all posts, optionally limit the number of results"""
    if limit:
        return list(text_posts.values())[:limit]
    return list(text_posts.values())


# GET single post by ID
@app.get("/posts/{post_id}")
def get_post(post_id: int) -> postresponse:
    """Get a single post by its ID"""
    if post_id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    return text_posts[post_id]

# ============ POST Methods ============

# POST - Create a new post
@app.post("/posts", status_code=201)
def create_post(post: postCreate) -> postresponse:
    """Create a new post"""
    new_id = max(text_posts.keys()) + 1
    new_post = {"title": post.title, "content": post.content}
    text_posts[new_id] = new_post
    return new_post

# ============ PUT Methods ============

@app.put("/posts/{post_id}")
def update_post(post_id: int, updated_post: postCreate) -> postresponse:
    if post_id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    text_posts[post_id] = {"title": updated_post.title, "content": updated_post.content}
    return text_posts[post_id]


# patch method 


@app.patch("/posts/{post_id}")
def patch_post(post_id: int, updated_post: postCreate) -> postresponse:
    if post_id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    existing_post = text_posts[post_id]
    if updated_post.title:
        existing_post["title"] = updated_post.title
    if updated_post.content:
        existing_post["content"] = updated_post.content
    text_posts[post_id] = existing_post
    return text_posts[post_id]


# ============ DELETE Methods ============

@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    if post_id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found")
    del text_posts[post_id]
    return None
