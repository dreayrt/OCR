import uuid
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_document_uuid() -> str:
    """Tạo UUID phiên bản 4 cho tài liệu."""
    return str(uuid.uuid4())


def safe_remove_file(file_path: Optional[str]) -> None:
    """Xóa file an toàn khỏi hệ thống, không làm gián đoạn flow nếu xảy ra lỗi."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Temporary file removed: {file_path}")
        except Exception as e:
            logger.warning(f"Could not remove temporary file {file_path}: {e}")
