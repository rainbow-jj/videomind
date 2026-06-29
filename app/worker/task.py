import json
import time
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.worker.celery_app import celery_app


def _sync_db_url(url: str) -> str:
    # 兼容你 async URL，例如 sqlite+aiosqlite -> sqlite
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///")
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    return url


@celery_app.task(name="videomind.full_pipeline")
def full_pipeline_task(job_id: str, video_id: str):
    engine = create_engine(_sync_db_url(settings.DATABASE_URL), future=True)

    table = "processing_jobs"

    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"""
                UPDATE {table}
                SET status='processing', progress=10, message='正在处理...'
                WHERE id=:id
                """),
                {"id": job_id},
            )

        # 模拟处理
        time.sleep(2)

        fake_result = {
            "summary": "这是第10天联调的占位结果",
            "video_id": video_id,
            "key_frames": 5,
        }

        with engine.begin() as conn:
            conn.execute(
                text(f"""
                    UPDATE {table}
                    SET status='done',
                        progress=100,
                        message='done',
                        result_json=:result_json,
                        error_message=NULL
                    WHERE id=:id
                """),
                {"id": job_id, "result_json": json.dumps(fake_result, ensure_ascii=False)},
            )
    except Exception as e:
        with engine.begin() as conn:
            conn.execute(
                text(f"""
                    UPDATE {table}
                    SET status='failed',
                        message='failed',
                        error_message=:err
                    WHERE id=:id
                """),
                {"id": job_id, "err": str(e)},
            )
        raise