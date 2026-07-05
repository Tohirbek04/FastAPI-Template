# 03 — Database: Django ORM'dan SQLAlchemy 2.0 async'ga

## Eng katta farq

Django ORM — **active record**: model o'zini o'zi saqlaydi (`user.save()`).
SQLAlchemy — **unit of work**: siz obyektlarni session'ga qo'shasiz, session
oxirida hammasini bitta tranzaksiyada yozadi. Session — Django'dagi
`transaction.atomic()` blokiga o'xshaydi, lekin har doim ishlaydi.

## Query taqqoslash jadvali

| Django ORM | SQLAlchemy 2.0 (bizdagi uslub) |
|---|---|
| `User.objects.get(pk=x)` | `await session.get(User, x)` |
| `User.objects.filter(email=e).first()` | `(await session.execute(select(User).where(User.email == e))).scalar_one_or_none()` |
| `User.objects.filter(active=True)[:20]` | `select(User).where(User.is_active).limit(20)` |
| `User.objects.create(...)` | `session.add(User(...)); await session.flush()` |
| `user.name = "x"; user.save()` | `user.name = "x"; await session.flush()` |
| `user.delete()` | `await session.delete(user)` |
| `select_related("profile")` (FK) | `select(User).options(selectinload(User.profile))` |
| `prefetch_related("orders")` (M2M/reverse) | xuddi shu `selectinload` |
| `get_object_or_404(User, pk=x)` | repository `get()` + `NotFoundError` (service'da) |
| `transaction.atomic()` | session allaqachon tranzaksiya; `get_db` commit qiladi |
| `.count()` | `await session.scalar(select(func.count()).select_from(User))` |

Amalda bu query'larning ko'pi `app/common/repository.py`dagi
`BaseRepository[T]` ichiga yashiringan — router/service'lar hech qachon xom
`select()` yozmaydi (bitta istisno: murakkab domenga xos query'lar
repository'da yoziladi, masalan `UserRepository.get_by_email`).

## Session hayoti: `get_db` (app/db/session.py)

```python
async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
        await session.commit()
```

Har HTTP request bitta session oladi (`Depends(get_db)`):

- handler muvaffaqiyatli tugasa → **commit**
- exception otilsa → commit'gacha yetmaydi, context manager **rollback** qiladi

Bu Django'dagi `ATOMIC_REQUESTS = True` bilan bir xil g'oya. Repository'lar
faqat `flush()` qiladi (SQL yuboriladi, lekin tranzaksiya ochiq qoladi) —
yakuniy qaror request oxirida.

## Async tuzoqlari (MUHIM)

1. **Lazy loading ishlamaydi.** Django'da `user.profile` kerak paytda
   yuklanadi. Async SQLAlchemy'da bu `MissingGreenlet` xatosini beradi —
   relationship'larni **oldindan** `selectinload` bilan yuklang.
2. **`expire_on_commit=False`** (bizda yoqilgan) — busiz commit'dan keyin
   obyekt maydonlariga tegish yashirin DB so'rovini keltirib chiqaradi
   (va async'da yiqiladi).
3. **Naive datetime yo'q.** `TimestampedBase` ustunlari
   `DateTime(timezone=True)` — Postgres'da `timestamptz`. Django'dagi
   `USE_TZ=True`ning ekvivalenti.

## Migratsiyalar: makemigrations → Alembic

| Django | Bu template |
|---|---|
| `./manage.py makemigrations` | `make makemigration m="add orders"` |
| `./manage.py migrate` | `make migrate` |
| `./manage.py migrate app 0003` | `uv run alembic downgrade <rev>` |
| `showmigrations` | `uv run alembic history` / `current` |
| app ichidagi `migrations/` | markaziy `migrations/versions/` |

Farqlar:

- Alembic autogenerate **faqat import qilingan modellarni ko'radi** — shuning
  uchun `app/db/registry.py` bor. Yangi model → registry'ga import → keyin
  makemigration. Buni unutish — eng ko'p uchraydigan xato.
- Django'dan farqli, autogenerate mukammal emas: **har migratsiya faylini
  ko'zdan kechiring** (ayniqsa index/constraint o'zgarishlari).
- Migratsiya URL'ni `alembic.ini`dan emas, `get_settings().database_url`dan
  oladi (`migrations/env.py`) — bitta haqiqat manbai.

## Test infratuzilmasi (tests/conftest.py)

Django'ning `TestCase` har testni tranzaksiyaga o'rab, oxirida rollback
qilganidek, bizning `db_session` fixture har testni **savepoint** ichida
ishlatadi:

```python
async with engine.connect() as conn:
    await conn.begin()
    session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    await conn.rollback()      # test yozgan hamma narsa bekor bo'ladi
```

Testlar `app_test` bazasida ishlaydi (avtomatik yaratiladi), jadvallar
`Base.metadata.create_all` bilan quriladi — migratsiyalar emas (tezlik uchun).
