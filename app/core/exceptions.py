from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class FileValidationError(AppException):
    """Raised when uploaded file fails validation (MIME, magic bytes, size, etc.)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="FILE_VALIDATION_ERROR", status_code=400, details=details)


class UnsupportedFileError(AppException):
    """Raised when file extension or format is unsupported."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="UNSUPPORTED_FILE_TYPE", status_code=415, details=details)


class PDFProcessingError(AppException):
    """Raised when PDF cannot be read, parsed, or rendered."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="PDF_PROCESSING_ERROR", status_code=422, details=details)


class OCRError(AppException):
    """Raised when OCR extraction fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="OCR_ERROR", status_code=500, details=details)


class LLMExtractionError(AppException):
    """Raised when LLM API call fails or returns unparseable output."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="LLM_EXTRACTION_ERROR", status_code=502, details=details)


class DataValidationError(AppException):
    """Raised when extracted data fails validation rules."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="DATA_VALIDATION_ERROR", status_code=422, details=details)


class DatabaseError(AppException):
    """Raised on database interaction failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="DATABASE_ERROR", status_code=500, details=details)


class ResourceNotFoundError(AppException):
    """Raised when a requested resource (document, page, record, job) is not found."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="RESOURCE_NOT_FOUND", status_code=404, details=details)
