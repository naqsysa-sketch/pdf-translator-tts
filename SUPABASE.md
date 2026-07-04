# Supabase (PostgreSQL) — دليل الربط

**مشروعك:** `hsqkkpcyriklncdysgpn`  
**لوحة التحكم:** https://supabase.com/dashboard/project/hsqkkpcyriklncdysgpn  
**API URL:** https://hsqkkpcyriklncdysgpn.supabase.co

Supabase = **PostgreSQL مُدار** في السحابة. المشروع يدعمه مباشرة عبر `DATABASE_URL` — لا حاجة لتغيير الكود.

## ماذا يحل Supabase؟

| المشكلة | مع Supabase |
|---------|-------------|
| بيانات Vercel تُمسح من `/tmp` | بيانات دائمة في السحابة |
| لا تريد إدارة PostgreSQL على VPS | قاعدة جاهزة |
| عدة مستخدمين ومشاريع | مناسب |

**ملاحظة:** مع تفعيل **Supabase Storage** (أدناه) يُحفظ PDF والصوت في السحابة. بدونه:
- **Redis** (لـ Celery) — أو `CELERY_TASK_ALWAYS_EAGER=true` على Vercel
- **ملفات MP3** — مؤقتة على Vercel (`/tmp`)

---

## خطوات الإعداد

### 1) أنشئ مشروعاً على [supabase.com](https://supabase.com)

### 2) انسخ Connection String

من **Project Settings → Database → Connection string**  
(أو: https://supabase.com/dashboard/project/hsqkkpcyriklncdysgpn/settings/database)

**لـ Vercel (Serverless)** — **Transaction pooler** (منفذ `6543`):

```env
DATABASE_URL=postgresql://postgres.hsqkkpcyriklncdysgpn:[PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require
```

> **مهم:** لا تستخدم `db....supabase.co:5432` على Vercel — يفشل بسبب IPv6. استخدم pooler أعلاه.

**لـ Docker / VPS / Celery worker** — **Direct connection** (منفذ `5432`):

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.hsqkkpcyriklncdysgpn.supabase.co:5432/postgres?sslmode=require
```

### 3) ضع المتغير في `.env` أو Vercel

**محلي:**
```bash
# .env
DATABASE_URL=postgresql://postgres.xxxx:password@....supabase.com:6543/postgres?sslmode=require
```

**Vercel Dashboard → Settings → Environment Variables:**
- `DATABASE_URL` = رابط الـ pooler (6543)
- `CELERY_TASK_ALWAYS_EAGER` = `true`

### 4) شغّل التطبيق

عند أول تشغيل، التطبيق ينشئ الجداول تلقائياً (`users`, `projects`, `chapters`).

```bash
uvicorn app:app --reload
# أو
docker compose up web worker
```

### 5) أنشئ مستخدم admin

```bash
python scripts/create_user.py --username admin
```

---

## Docker + Supabase (بدون حاوية db محلية)

في `.env`:

```env
DATABASE_URL=postgresql://...@....supabase.com:5432/postgres?sslmode=require
```

في `docker-compose.prod.yml` يمكنك **تعطيل** خدمة `db` واستخدام `DATABASE_URL` من `.env` فقط للـ `web` و `worker`.

---

## الجداول التي تُنشأ تلقائياً

| الجدول | المحتوى |
|--------|---------|
| `users` | الحسابات وكلمات المرور |
| `projects` | كتب PDF المرفوعة |
| `chapters` | الفصول، الترجمة، روابط الصوت |

يمكنك معاينتها من **Supabase → Table Editor**.

---

## استكشاف الأخطاء

| الخطأ | الحل |
|-------|------|
| `SSL required` | أضف `?sslmode=require` لنهاية الرابط |
| `connection refused` | تأكد من المنفذ (6543 لـ Vercel، 5432 لـ Docker) |
| `password authentication failed` | انسخ كلمة المرور من Database settings |
| Celery لا يكتب للـ DB | استخدم Direct connection (5432) للـ worker |

---

## Supabase Storage (ملفات PDF و MP3)

لحفظ **الصوت وملف PDF الأصلي** بشكل دائم (بدلاً من `/tmp` على Vercel):

### 1) أنشئ bucket باسم `media`

من **Storage → New bucket** → الاسم: `media` (خاص / private)

### 2) أضف متغيرات البيئة

```env
SUPABASE_URL=https://hsqkkpcyriklncdysgpn.supabase.co
SUPABASE_SERVICE_KEY=eyJ...   # من Settings → API → service_role (سري!)
SUPABASE_STORAGE_BUCKET=media
```

> استخدم **service_role** وليس `anon` — مطلوب للرفع من الخادم.

### 3) على Vercel

أضف نفس المتغيرات في **Environment Variables** ثم أعد النشر.

### ماذا يُخزَّن؟

| الملف | المسار |
|-------|--------|
| PDF الأصلي | `pdfs/{project_id}.pdf` |
| صوت الفصل | `audio/{hash}.mp3` |
| معاينة الصوت | `previews/preview_*.mp3` |

الروابط في المتصفح تُولَّد كـ **Signed URL** مؤقتة (افتراضياً 7 أيام).
