"""Alembic autogenerate va testlar uchun barcha modellarni import qiladi.

Yangi domen modeli qo'shilganda BU YERGA import qo'shing —
aks holda Alembic migratsiyada jadvalni ko'rmaydi.
"""

from app.users.models import User

__all__ = ["User"]
