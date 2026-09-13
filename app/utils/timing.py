import time
from contextlib import contextmanager
from typing import Generator, Dict, Any
from app.core.logging import logger


@contextmanager
def measure_time(stage_name: str, extra: Dict[str, Any] = None) -> Generator[Dict[str, float], None, None]:
    """Context manager to measure execution time of a processing stage."""
    start_time = time.perf_counter()
    metrics = {"duration_ms": 0.0}
    try:
        yield metrics
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics["duration_ms"] = elapsed_ms
        log_extra = extra.copy() if extra else {}
        log_extra["processing_stage"] = stage_name
        log_extra["execution_time_ms"] = round(elapsed_ms, 2)
        logger.info(f"Stage '{stage_name}' completed in {elapsed_ms:.2f} ms", extra=log_extra)
