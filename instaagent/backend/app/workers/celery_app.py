# backend/app/workers/celery_app.py
# ─────────────────────────────────────────────────────────────────────────────
# InstaAgent — Enterprise Celery + Beat Configuration
# Workers:   photo_worker, post_worker
# New workers: instagram_token_refresher, telegram_broadcast
# Beat tasks run on IST timezone (Asia/Kolkata).
# ─────────────────────────────────────────────────────────────────────────────

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "instaagent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.photo_worker",
        "app.workers.post_worker",
        "app.workers.instagram_token_refresher",
        "app.workers.telegram_broadcast",
        "app.workers.whatsapp_worker",
    ],
)

# SSL config required for Upstash Redis (rediss:// scheme)
_ssl = {"ssl_cert_reqs": None}

celery_app.conf.update(
    # ── Serialisation ─────────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # ── Timezone (IST) ────────────────────────────────────────────────────────
    timezone="Asia/Kolkata",
    enable_utc=True,

    # ── Reliability ───────────────────────────────────────────────────────────
    broker_connection_retry_on_startup=True,
    broker_pool_limit=10,
    broker_transport_options={
        "visibility_timeout": 3600,
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
        "socket_keepalive": True,
        "retry_on_timeout": True,
    },
    redis_backend_health_check_interval=30,

    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_annotations={"*": {"max_retries": 3, "default_retry_delay": 30}},

    # ── Redis SSL ─────────────────────────────────────────────────────────────
    broker_use_ssl=_ssl,
    redis_backend_use_ssl=_ssl,

    # ── Windows Compatibility ─────────────────────────────────────────────────
    # On Windows, Python uses 'spawn' for multiprocessing which breaks Celery's
    # default prefork pool. Use 'solo' pool for local dev.
    # In production (Linux), remove this line — prefork works fine there.
    worker_pool="solo",

    # ── Beat Schedule ─────────────────────────────────────────────────────────
    beat_schedule={
        # Every 60 seconds — check for scheduled posts due for publishing
        "publish-scheduled-posts": {
            "task":     "app.workers.post_worker.publish_scheduled_posts",
            "schedule": 60.0,
        },

        # Daily at 3:00 AM IST — refresh Instagram tokens expiring in 7 days
        "refresh-instagram-tokens": {
            "task":     "app.workers.instagram_token_refresher.refresh_expiring_tokens",
            "schedule": crontab(hour=3, minute=0),
        },

        # Every Monday at 9:00 AM IST — send weekly analytics reports
        "send-weekly-reports": {
            "task":     "app.workers.telegram_broadcast.send_weekly_reports_task",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
        },

        # 1st of every month at 9:00 AM IST — send monthly analytics reports
        "send-monthly-reports": {
            "task":     "app.workers.telegram_broadcast.send_monthly_reports_task",
            "schedule": crontab(hour=9, minute=0, day_of_month=1),
        },
    },
)