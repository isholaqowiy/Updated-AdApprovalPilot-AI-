"""Security helpers: single-source-of-truth admin identity check."""
from config import settings


def is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id
