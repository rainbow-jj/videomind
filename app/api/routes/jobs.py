from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.core.db import get_db
from app.models.processing_job import ProcessingJob
from app.models.video import Video
from app.models.job_stage import JobStage
from app.schemas.job import (
    JobCreateIn,
    JobOut,
    APIResponse,
    JobListOut,
    JobStageOut,
    JobRetryOut,
)
from app.worker.task import full_pipeline_task

router = APIRouter(prefix="/api/v1/jobs", tags=["任务管理"])


@router.post("", response_model=JobOut)
async def create_job(req: JobCreateIn, db: AsyncSession = Depends(get_db)):
    video = await db.get(Video, req.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="video not found")

    job = ProcessingJob(
        video_id=req.video_id,
        job_type=req.job_type,
        status="queued",
        progress=0,
        message="job queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    celery_task = full_pipeline_task.delay(str(job.id), str(req.video_id))
    job.celery_task_id = celery_task.id
    await db.commit()
    await db.refresh(job)

    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


# 新增 1: 列表
@router.get("", response_model=APIResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    video_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(ProcessingJob.status == status)
    if video_id:
        filters.append(ProcessingJob.video_id == video_id)

    total_stmt = select(func.count()).select_from(ProcessingJob)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = select(ProcessingJob)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(ProcessingJob.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()

    items = [
        JobOut(
            id=str(r.id),
            video_id=str(r.video_id),
            job_type=r.job_type,
            status=r.status,
            progress=r.progress,
            message=r.message or "",
            error_message=r.error_message,
            celery_task_id=r.celery_task_id,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]

    return APIResponse(data=JobListOut(items=items, total=total, page=page, size=size))


# 新增 2: stages
@router.get("/{job_id}/stages", response_model=APIResponse)
async def get_job_stages(job_id: str, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    rows = (
        await db.execute(
            select(JobStage).where(JobStage.job_id == job_id).order_by(JobStage.created_at.asc())
        )
    ).scalars().all()

    data = []
    for r in rows:
        duration_ms = None
        if r.started_at and r.finished_at:
            duration_ms = int((r.finished_at - r.started_at).total_seconds() * 1000)

        data.append(
            JobStageOut(
                stage=r.stage,
                status=r.status,
                progress=r.progress,
                started_at=r.started_at,
                finished_at=r.finished_at,
                duration_ms=duration_ms,
                error_message=r.error_message,
            )
        )

    return APIResponse(data=data)


# 新增 3: retry
@router.post("/{job_id}/retry", response_model=APIResponse)
async def retry_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="only failed job can retry")

    await db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id == job_id)
        .values(
            status="queued",
            progress=0,
            message="retried",
            error_message=None,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(delete(JobStage).where(JobStage.job_id == job_id))
    await db.commit()

    celery_task = full_pipeline_task.delay(str(job.id), str(job.video_id))

    await db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.id == job_id)
        .values(celery_task_id=celery_task.id, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return APIResponse(
        message="retried",
        data=JobRetryOut(job_id=str(job_id), celery_task_id=celery_task.id, status="queued"),
    )