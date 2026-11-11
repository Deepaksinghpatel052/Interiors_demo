"""Upload validation: type (by extension and real content) and size."""
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
DOC_EXTS = {"pdf", "jpg", "jpeg", "png", "webp", "txt"}


def _check_size(f):
    limit = getattr(settings, "MAX_UPLOAD_MB", 8) * 1024 * 1024
    if f.size and f.size > limit:
        raise ValidationError(f"File is too large. The maximum size is {settings.MAX_UPLOAD_MB} MB.")


def _ext(f):
    return f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""


def validate_image(f):
    _check_size(f)
    if _ext(f) not in IMAGE_EXTS:
        raise ValidationError("Please upload a JPG, PNG or WebP image.")
    try:
        pos = f.tell() if hasattr(f, "tell") else 0
        Image.open(f).verify()
        f.seek(pos)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("This file is not a valid image.")


def validate_document(f):
    _check_size(f)
    ext = _ext(f)
    if ext not in DOC_EXTS:
        raise ValidationError("Please upload a PDF, image or text file.")
    if ext == "pdf":
        pos = f.tell() if hasattr(f, "tell") else 0
        head = f.read(5)
        f.seek(pos)
        if head != b"%PDF-":
            raise ValidationError("This file is not a valid PDF.")
    elif ext in IMAGE_EXTS:
        validate_image(f)
