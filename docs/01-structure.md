# 01 — Loyiha strukturasi: Django apps'dan domen papkalariga

## Django'da bunday edi

```
Django-Template/                 FastAPI-Template/
├── conf/                        ├── app/
│   ├── settings/                │   ├── core/config.py
│   └── urls.py                  │   └── main.py (include_router'lar)
├── apps/                        │
│   ├── users/                   │   ├── users/
│   │   ├── models.py            │   │   ├── models.py
│   │   ├── serializers.py       │   │   ├── schemas.py
│   │   ├── views.py             │   │   ├── router.py + service.py
│   │   └── urls.py              │   │   └── (router prefix main.py'da)
│   └── common/                  │   ├── common/ + db/
└── manage.py                    └── Makefile (manage.py o'rnida)
```

FastAPI'da rasmiy "app" tushunchasi yo'q — lekin biz Django'dagi kabi
**domen-birinchi** strukturani qo'lladik (Netflix Dispatch va
fastapi-best-practices community standarti). Har domen o'z papkasida to'liq.

## Har qatlamning vazifasi

| Fayl | Django ekvivalenti | Vazifasi |
|---|---|---|
| `users/models.py` | `models.py` | SQLAlchemy jadval modeli — faqat DB shakli |
| `users/schemas.py` | `serializers.py` | Pydantic — API kirish/chiqish shakli |
| `users/repository.py` | `Model.objects` manager | Barcha DB query'lar shu yerda |
| `users/service.py` | view ichidagi biznes logika | Qoidalar, tranzaksiya oqimi |
| `users/router.py` | `views.py` + `urls.py` | Faqat HTTP: status kodlar, DI |
| `auth/deps.py` | DRF `permissions/authentication` | `get_current_user` dependency |
| `users/tasks.py` | `tasks.py` (Celery) | Taskiq background task'lar |

## Oltin qoidalar

1. **Router faqat HTTP bilan ishlaydi.** Query yozmaydi, parol hash'lamaydi —
   service chaqiradi, natijani schema'ga o'raydi. `app/users/router.py`ga
   qarang: har handler 3-5 qator.
2. **Service HTTP'ni bilmaydi.** U `HTTPException` emas, domain xato tashlaydi
   (`ConflictError`, `UnauthorizedError` — `app/core/exceptions.py`).
   Handler'lar ularni JSON'ga o'giradi. Shu tufayli service'ni HTTP'siz
   (masalan, task ichida) ham ishlatish mumkin.
3. **Repository faqat query.** Biznes qaror qabul qilmaydi. Umumiy CRUD
   `app/common/repository.py`dagi `BaseRepository[T]`dan meros olinadi —
   Django'dagi `objects` manager'ga o'xshaydi, lekin **explicit dependency**:
   testda mock qilish oson, global holat yo'q.
4. **Versiya prefiksi markazda.** `/api/v1` faqat `app/main.py`dagi
   `include_router(...)` chaqiruvlarida. Domen router'lari versiyani bilmaydi —
   v2 chiqsa, faqat main.py o'zgaradi.

## Nega alohida `models.py` va `schemas.py`?

Django'da model ham DB, ham (serializer orqali) API shakli bo'lib ketadi.
Bizda:

- `models.py` — DB haqiqati (`hashed_password` bor)
- `schemas.py` — API kontrakti (`UserRead`da `hashed_password` YO'Q)

API javobida maxfiy maydon sizib chiqishi arxitektura darajasida imkonsiz.

## Yangi domen qo'shish (checklist)

Masalan, `orders` domeni:

1. `app/orders/` papkasini yarating: `__init__.py`, `models.py`, `schemas.py`,
   `repository.py`, `service.py`, `router.py`
2. `models.py`da model yozing (`TimestampedBase`dan meros — UUID pk,
   `created_at`/`updated_at` avtomatik)
3. **`app/db/registry.py`ga import qo'shing** — busiz Alembic jadvalni
   ko'rmaydi:
   ```python
   from app.orders.models import Order
   ```
4. `make makemigration m="create orders table"` → faylni ko'zdan kechiring →
   `make migrate`
5. `app/main.py`da router'ni ulang:
   ```python
   app.include_router(orders_router, prefix="/api/v1/orders", tags=["orders"])
   ```
6. `tests/test_orders_api.py` yozing (conftest'dagi `client` va `db_session`
   fixture'lari tayyor)

Domen keraksiz bo'lib qolsa — bitta papka + bitta registry qator + bitta
include_router o'chadi. Kelajakda microservice'ga ajratish ham shu chegara
bo'ylab kesiladi.
