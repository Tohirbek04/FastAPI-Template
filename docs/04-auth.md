# 04 — Auth: contrib.auth'dan qo'lda yozilgan JWT'ga

## Django'da bunday edi

`django.contrib.auth` + session cookie: login qilganda server session yozadi,
brauzer cookie olib yuradi. DRF'da ko'pincha `TokenAuthentication` yoki
SimpleJWT qo'shiladi.

## Bu template'da: stateless JWT

Server hech qanday session saqlamaydi. Login'da ikkita imzolangan token
beriladi:

```
POST /api/v1/auth/register  → 201 UserRead
POST /api/v1/auth/login     → {access_token, refresh_token, token_type}
POST /api/v1/auth/refresh   → yangi juftlik
GET  /api/v1/users/me       → Authorization: Bearer <access>
```

- **access** — 15 daqiqa (env: `ACCESS_TOKEN_TTL_MIN`). Har so'rovda yuboriladi.
- **refresh** — 7 kun (env: `REFRESH_TOKEN_TTL_DAYS`). Faqat `/refresh`ga
  yuboriladi, yangi juftlik olish uchun.

Token payload'i: `{"sub": "<user uuid>", "type": "access|refresh", "iat", "exp"}`.
`type` claim'i refresh tokenni access sifatida ishlatishni (va aksincha)
taqiqlaydi — `decode_token(token, expected_type=...)` tekshiradi
(`app/core/security.py`).

## Nega PyJWT + pwdlib (python-jose/passlib EMAS)

Ko'p eski tutorial'lar `python-jose` + `passlib` ishlatadi. Ulardan qoching:

| Kutubxona | Muammo |
|---|---|
| python-jose | CVE-2024-33663 (ECDSA algorithm confusion), CVE-2024-33664 (JWE DoS); yillab qarovsiz |
| passlib | Oxirgi reliz 2020; bcrypt≥4.1 bilan `AttributeError` berib sinadi |
| **PyJWT** ✅ | Faol maintained; FastAPI rasmiy docs ham shunga o'tgan |
| **pwdlib[argon2]** ✅ | Zamonaviy passlib o'rinbosari; Argon2id — parol hashing bo'yicha hozirgi tavsiya |

Xavfsizlik detallari (`app/core/security.py`, `app/auth/service.py`):

- `jwt.decode(..., algorithms=["HS256"])` — algoritm **qat'iy pin qilingan**.
  Busiz "alg confusion" hujumi mumkin.
- Login'da email topilmasa ham dummy-hash verify bajariladi (`_DUMMY_HASH`) —
  javob vaqti bir xil, email mavjudligini **timing** orqali bilib bo'lmaydi.
- Noto'g'ri email ham, noto'g'ri parol ham bitta xabar qaytaradi:
  `"Incorrect email or password"` — user enumeration'ga qarshi.
- Parol siyosati: min 8 belgi (`RegisterRequest`da Field constraint).

## get_current_user — DRF permission'larning ekvivalenti

`app/auth/deps.py`:

```python
CurrentUser = Annotated[User, Depends(get_current_user)]

@router.get("/me")
async def read_me(current_user: CurrentUser) -> UserRead: ...
```

| DRF | Bu template |
|---|---|
| `permission_classes = [IsAuthenticated]` | parametrda `current_user: CurrentUser` |
| `IsAdminUser` | `if not current_user.is_superuser: raise PermissionDeniedError` (users/router.py'dagi list misoli) |
| `request.user` | `current_user` (tipli!) |

Dependency zanjiri: `OAuth2PasswordBearer` header'dan tokenni oladi →
`decode_token` tekshiradi → `UserRepository.get` bazadan yuklaydi →
`is_active` tekshiriladi. Har bosqich yiqilsa — 401.

## Ongli qabul qilingan tradeoff'lar (production'da kuchaytiring)

1. **Refresh token rotation yo'q** — o'g'irlangan refresh token muddati
   tugaguncha ishlayveradi. Kuchaytirish: har refresh'da `jti` claim'ini
   Redis'da belgilash (ishlatilgan tokenni rad etish) yoki User'ga
   `token_version` ustuni qo'shib, logout/parol o'zgarishida oshirish.
2. **Register 409 qaytaradi** — email band ekani bilinadi. To'liq yechim
   email-verification oqimi talab qiladi (template'da email infratuzilmasi
   YAGNI deb chiqarilgan). Endpoint 10/min rate-limit bilan himoyalangan.
3. **Logout endpoint'i yo'q** — stateless JWT'da server tomonida bekor
   qilinadigan narsa yo'q; klient tokenlarni o'chiradi. Server-side bekor
   qilish kerak bo'lsa — 1-banddagi yechimlardan foydalaning.
