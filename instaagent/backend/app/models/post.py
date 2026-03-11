# backend/app/models/post.py
# Pydantic models for Post API requests and responses

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PostCreate(BaseModel):
    """Used for validating incoming post creation requests."""
    product_name: str
    product_type: str = "other"
    additional_info: str = ""


class PostResponse(BaseModel):
    """Returned by GET /posts and GET /posts/{post_id}"""
    id: str
    user_id: str
    product_name: str
    product_type: Optional[str] = None
    additional_info: Optional[str] = None
    original_photo_url: Optional[str] = None
    edited_photo_url: Optional[str] = None
    caption_hindi: Optional[str] = None
    caption_english: Optional[str] = None
    hashtags: Optional[List[str]] = []
    status: str                             # processing|ready|scheduled|posted|failed
    platform: str = "instagram"
    scheduled_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    instagram_post_id: Optional[str] = None
    instagram_permalink: Optional[str] = None
    likes_count: int = 0
    comments_count: int = 0
    reach: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    """Paginated list of posts."""
    posts: List[PostResponse]
    page: int
    page_size: int
    total: Optional[int] = None


class PublishResponse(BaseModel):
    """Returned after successfully posting to Instagram."""
    status: str
    instagram_post_id: str
    permalink: str


class ScheduleRequest(BaseModel):
    """Request body for scheduling a post."""
    scheduled_at: datetime


class ScheduleResponse(BaseModel):
    status: str
    scheduled_at: str
