"""In-process job manager for long-running forecast tasks.

Provides:
    * A `JobManager` that accepts coroutine / callable submissions and runs them
      on a thread pool (CPU-bound forecast work benefits from threads because
      most of the heavy lifting happens inside numpy/statsmodels which release
      the GIL during C-level work).
    * Status tracking: PENDING -> RUNNING -> COMPLETED / FAILED
    * Progress callbacks so a job can publish incremental state
    * Disk-backed persistence of job state to /app/data/jobs.json so a status
      query survives a process restart.
    * Automatic eviction of completed jobs after a TTL to keep memory bounded.

This keeps the API responsive: a forecast request returns immediately with a
job_id, and the client polls the status endpoint. For very large datasets this
is essential because a single forecast can take 30-90 s.
"""
from __future__ import annotations

import json
import json as _json
import logging
import os
import threading
import time
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .config import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobInfo:
    job_id: str
    job_type: str  # 'forecast', 'analyze', etc.
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0..1
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    request: Optional[Dict[str, Any]] = None

    def to_public(self) -> Dict[str, Any]:
        """Return a JSON-serializable view (excluding the heavy result)."""
        d = asdict(self)
        d["status"] = self.status.value
        # Don't dump the result in the public status — it's large
        d.pop("result", None)
        return d


class JobManager:
    """Thread-pool backed job manager with disk persistence."""

    _instance: Optional["JobManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # Singleton — share a single executor across the app
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: Optional[int] = None) -> None:
        if self._initialized:
            return
        # Cap workers: too many threads -> thrashing on large DataFrames.
        # For CPU-bound ML we want roughly #cores, with some headroom.
        cpu = os.cpu_count() or 4
        if max_workers is None:
            # Use min(cores, 4) for safety; for tiny machines this still runs
            # sequentially. For larger machines we get parallelism.
            max_workers = max(2, min(cpu, 4))
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fiq-job",
        )
        self._jobs: Dict[str, JobInfo] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._persist_path = Path(settings.DATA_DIR) / "jobs.json"
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()
        self._initialized = True
        logger.info("JobManager initialized with %d workers", max_workers)

    # ----------------------------------------------------- public API
    def submit(
        self,
        job_type: str,
        func: Callable[..., Any],
        *,
        request: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
        **kwargs: Any,
    ) -> str:
        """Submit a job. Returns the job_id immediately."""
        job_id = uuid.uuid4().hex
        job = JobInfo(job_id=job_id, job_type=job_type, request=request)
        with self._lock:
            self._jobs[job_id] = job
        # Wrap func so we can track status + progress + exception
        def _runner() -> Any:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat() + "Z"
            if on_progress:
                on_progress(0.05, "Started")
            self._persist()
            try:
                result = func(**kwargs)
                job.result = result
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.message = "Done"
                return result
            except Exception as e:
                logger.exception("Job %s failed", job_id)
                job.status = JobStatus.FAILED
                job.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                raise
            finally:
                job.finished_at = datetime.utcnow().isoformat() + "Z"
                self._persist()

        fut = self._executor.submit(_runner)
        with self._lock:
            self._futures[job_id] = fut
        return job_id

    def get(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)

    def status(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.get(job_id)
        if not job:
            return None
        return job.to_public()

    def result(self, job_id: str, timeout: Optional[float] = None) -> Any:
        """Block until the job completes and return its result."""
        fut = self._futures.get(job_id)
        if fut is None:
            job = self.get(job_id)
            if not job:
                raise KeyError(f"Unknown job_id: {job_id}")
            if job.status == JobStatus.COMPLETED:
                return job.result
            if job.status == JobStatus.FAILED:
                raise RuntimeError(job.error or "Job failed")
            raise RuntimeError(f"Job in state {job.status}")
        return fut.result(timeout=timeout)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            fut = self._futures.get(job_id)
            if fut and not fut.done():
                return fut.cancel()
        return False

    def list_jobs(self, job_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_public() for j in jobs[:limit]]

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """Remove jobs older than max_age_seconds. Returns # removed."""
        now = time.time()
        with self._lock:
            to_remove = []
            for jid, j in self._jobs.items():
                if j.finished_at:
                    try:
                        ft = datetime.fromisoformat(j.finished_at.rstrip("Z")).timestamp()
                    except Exception:
                        continue
                    if now - ft > max_age_seconds:
                        to_remove.append(jid)
            for jid in to_remove:
                self._jobs.pop(jid, None)
                self._futures.pop(jid, None)
        if to_remove:
            self._persist()
        return len(to_remove)

    # ----------------------------------------------------- persistence
    def _persist(self) -> None:
        """Atomically write the current jobs state to disk.

        We persist the lightweight public view; the result is written
        separately by the caller (e.g. storage.save_forecast).
        """
        try:
            with self._lock:
                data = {jid: j.to_public() for jid, j in self._jobs.items()}
            tmp = self._persist_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
            os.replace(tmp, self._persist_path)
        except Exception as e:
            logger.warning("Failed to persist job state: %s", e)

    def _load_from_disk(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                for jid, jd in data.items():
                    self._jobs[jid] = JobInfo(
                        job_id=jd["job_id"],
                        job_type=jd["job_type"],
                        status=JobStatus(jd.get("status", "pending")),
                        progress=jd.get("progress", 0.0),
                        message=jd.get("message", ""),
                        result=None,  # results not persisted in the index
                        error=jd.get("error"),
                        created_at=jd.get("created_at", ""),
                        started_at=jd.get("started_at"),
                        finished_at=jd.get("finished_at"),
                        request=jd.get("request"),
                    )
        except Exception as e:
            logger.warning("Failed to load jobs from disk: %s", e)


class RedisJobManager:
    """Redis-backed job manager for multi-process deployments."""

    def __init__(self, redis_url: str):
        import redis
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._prefix = "fiq:jobs:"
        self._result_prefix = "fiq:results:"
        logger.info("RedisJobManager connected to %s", redis_url)

    def submit(self, job_id: str, func, *args, **kwargs) -> str:
        import threading
        job_info = JobInfo(
            job_id=job_id,
            status="PENDING",
            progress=0.0,
            message="Queued",
            created_at=time.time(),
        )
        self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job_info.to_dict()))
        def _runner():
            job_info.status = "RUNNING"
            job_info.started_at = time.time()
            self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job_info.to_dict()))
            try:
                result = func(*args, **kwargs)
                job_info.status = "COMPLETED"
                job_info.progress = 1.0
                job_info.message = "Done"
                job_info.finished_at = time.time()
                self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job_info.to_dict()))
                self._redis.set(f"{self._result_prefix}{job_id}", _json.dumps(result) if isinstance(result, dict) else str(result))
            except Exception as e:
                job_info.status = "FAILED"
                job_info.message = str(e)
                job_info.finished_at = time.time()
                self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job_info.to_dict()))
        t = threading.Thread(target=_runner, daemon=True, name=f"fiq-redis-{job_id[:8]}")
        t.start()
        return job_id

    def get_job(self, job_id: str):
        raw = self._redis.get(f"{self._prefix}{job_id}")
        if raw:
            data = _json.loads(raw)
            info = JobInfo(job_id=job_id)
            for k, v in data.items():
                setattr(info, k, v)
            return info
        return None

    def get_result(self, job_id: str):
        raw = self._redis.get(f"{self._result_prefix}{job_id}")
        if raw:
            try:
                return _json.loads(raw)
            except Exception:
                return raw
        return None

    def update_progress(self, job_id: str, progress: float, message: str = ""):
        job = self.get_job(job_id)
        if job:
            job.progress = progress
            if message:
                job.message = message
            self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job.to_dict()))

    def update_status(self, job_id: str, status: str, message: str = ""):
        job = self.get_job(job_id)
        if job:
            job.status = status
            if message:
                job.message = message
            if status == "RUNNING":
                job.started_at = time.time()
            elif status in ("COMPLETED", "FAILED", "CANCELLED"):
                job.finished_at = time.time()
            self._redis.set(f"{self._prefix}{job_id}", _json.dumps(job.to_dict()))

    def list_jobs(self, limit: int = 50):
        keys = self._redis.keys(f"{self._prefix}*")[:limit]
        jobs = []
        for key in keys:
            raw = self._redis.get(key)
            if raw:
                data = _json.loads(raw)
                info = JobInfo(job_id=data.get("job_id", ""))
                for k, v in data.items():
                    setattr(info, k, v)
                jobs.append(info.to_public())
        return sorted(jobs, key=lambda j: j.get("created_at", 0), reverse=True)

    def cleanup(self, max_age_seconds: int = 3600):
        cutoff = time.time() - max_age_seconds
        for key in self._redis.scan_iter(f"{self._prefix}*"):
            raw = self._redis.get(key)
            if raw:
                data = _json.loads(raw)
                if data.get("finished_at", 0) < cutoff and data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                    self._redis.delete(key)


_job_manager = None

def get_job_manager():
    global _job_manager
    if _job_manager is None:
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            try:
                _job_manager = RedisJobManager(redis_url)
            except Exception as e:
                logger.warning("Redis unavailable, falling back to in-memory jobs: %s", e)
                _job_manager = JobManager()
        else:
            _job_manager = JobManager()
    return _job_manager
