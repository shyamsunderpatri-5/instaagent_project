# backend/app/models/aggregator.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class AggregatorAccountBase(BaseModel):
    instagram_username: str = Field(..., pattern="^[a-zA-Z0-9._]+$")
    account_type: str = Field(..., pattern="^(owned|competitor)$")

class AggregatorAccountCreate(AggregatorAccountBase):
    access_token: Optional[str] = None

class AggregatorAccount(AggregatorAccountBase):
    id: UUID
    user_id: UUID
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AggregatedPostBase(BaseModel):
    ig_post_id: str
    caption: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    likes: int = 0
    comments: int = 0
    hashtags: List[str] = []
    posted_at: datetime

class AggregatedPost(AggregatedPostBase):
    id: UUID
    aggregator_account_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class AIInsightRequest(BaseModel):
    account_ids: List[UUID]

class AIInsightResponse(BaseModel):
    post_ideas: List[str]
    trend_summaries: List[str]
    best_posting_times: List[str]
    caption_suggestions: List[str]
    generated_at: datetime = Field(default_factory=datetime.now)
