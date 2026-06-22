"""Worker management endpoints for job queue processing."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_db
from app.worker import process_jobs_batch

router = APIRouter(prefix="/worker", tags=["worker"])


@router.post("/drain")
def drain_jobs(
    db: Session = Depends(get_db),
    x_cron_secret: str | None = Header(None),
) -> dict[str, int | list[str]]:
    """
    Process jobs from the queue in a batch.
    
    Requires X-Cron-Secret header matching CRON_SECRET env var.
    Used by Vercel Cron Jobs to trigger periodic job processing.
    Can also be called manually for testing.
    
    Returns:
        - processed: number of jobs successfully completed
        - failed: number of jobs that failed
        - errors: list of error messages from failed jobs
    """
    # Verify cron secret for security (prevents unauthorized job processing)
    cron_secret = os.getenv("CRON_SECRET", "")
    if not cron_secret or x_cron_secret != cron_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing CRON_SECRET header",
        )

    # Process up to 20 jobs in this batch (fits within 60s Vercel function timeout)
    result = process_jobs_batch(db, max_jobs=20)
    return result
