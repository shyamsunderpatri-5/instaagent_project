# backend/app/models/aggregator.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID

class AggregatorAccountBase(BaseModel):
    instagram_username: str = Field(..., pattern="^[a-zA-Z0-9._]+$")
    account_type: str = Field(..., pattern="^(owned|competitor)$")

class AggregatorAccountCreate(AggregatorAccountBase):
    access_token: Optional[str] = None

class AggregatorAccount(AggregatorAccountBase):
    id: UUID
    last_synced_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    alert_enabled: bool = True
    alert_threshold_er: float = Field(default=3.0, ge=0.5, le=20.0)
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
    engagement_rate: float = 0.0
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
    content_sentiment: Optional[str] = None
    top_format: Optional[str] = None
    weak_spots: Optional[List[str]] = []
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentFormatStats(BaseModel):
    media_type: str
    avg_engagement: float
    post_count: int

class ContentFormatResponse(BaseModel):
    formats: List[ContentFormatStats]

class FrequencyStats(BaseModel):
    day: str
    owned_count: int
    competitor_avg_count: float

class FrequencyResponse(BaseModel):
    heatmap: List[FrequencyStats]
    avg_per_week_owned: float
    avg_per_week_competitor: float

class AccountComparisonStats(BaseModel):
    username: str
    followers: int
    avg_engagement: float
    posts_per_week: float
    top_hashtags: List[str]

class ComparisonResponse(BaseModel):
    owned: Optional[AccountComparisonStats] = None
    competitors: List[AccountComparisonStats]

class HashtagStats(BaseModel):
    tag: str
    avg_engagement: float
    count: int

class HashtagResponse(BaseModel):
    hashtags: List[HashtagStats]

class AlertSettingsUpdate(BaseModel):
    alert_enabled: bool
    alert_threshold_er: float = Field(..., ge=0.5, le=20.0)
