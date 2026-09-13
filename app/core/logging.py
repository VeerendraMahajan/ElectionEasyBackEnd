import logging
import sys
import json
import time
from typing import Any, Dict
from contextvars import ContextVar

# Context variables for request and task tracking
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
job_id_ctx: ContextVar[str] = ContextVar("job_id", default="")
document_id_ctx: ContextVar[str] = ContextVar("document_id", default="")


class StructuredJsonFormatter(logging.Formatter):
    """
    JSON formatter for production logging with contextual correlation IDs.
    Redacts personal voter data from logs to respect privacy.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject context variables if set
        req_id = request_id_ctx.get()
        if req_id:
            log_data["request_id"] = req_id

        job_id = job_id_ctx.get()
        if job_id:
            log_data["job_id"] = job_id

        doc_id = document_id_ctx.get()
        if doc_id:
            log_data["document_id"] = doc_id

        # Include structured extras if present
        for key in ["page_number", "record_id", "processing_stage", "execution_time_ms", "count"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        root_logger.addHandler(handler)

    # Silence verbose third-party loggers
    for noisy_logger in ["urllib3", "pdfminer", "fitz", "PIL", "asyncio", "torch"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    return logging.getLogger("electoral_extractor")


logger = setup_logging()
