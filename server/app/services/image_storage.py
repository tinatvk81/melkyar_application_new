import os
import uuid

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
EXTENSION_BY_CONTENT_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

# پوشه‌ی server (والدِ پوشه‌ی app) — همان پوشه‌ای که scripts/backup.py هم برای media انتظار دارد
_SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MEDIA_ROOT_PATH = os.path.join(_SERVER_ROOT, settings.MEDIA_ROOT)


def property_media_dir(property_id: int) -> str:
    path = os.path.join(MEDIA_ROOT_PATH, "properties", str(property_id))
    os.makedirs(path, exist_ok=True)
    return path


def save_image_file(property_id: int, content_type: str, file_bytes: bytes) -> str:
    """فایل را با یک نام تصادفی (uuid) روی دیسک ذخیره می‌کند و همان نام را برمی‌گرداند.
    نام تصادفی هم از تداخل نام فایل جلوگیری می‌کند، هم از حملات مسیر (Path Traversal)."""
    ext = EXTENSION_BY_CONTENT_TYPE.get(content_type, ".jpg")
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(property_media_dir(property_id), stored_filename)
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    return stored_filename


def get_image_path(property_id: int, stored_filename: str) -> str:
    return os.path.join(property_media_dir(property_id), stored_filename)


def delete_image_file(property_id: int, stored_filename: str) -> None:
    path = get_image_path(property_id, stored_filename)
    if os.path.exists(path):
        os.remove(path)
