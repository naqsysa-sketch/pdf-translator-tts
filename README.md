# PDF Translator & TTS

منصة لرفع كتب PDF، تقسيمها إلى فصول، ترجمتها للعربية، وتحويلها إلى ملفات صوتية.

## المتطلبات

- Python 3.11+
- Redis (للمهام الخلفية)
- FFmpeg وTesseract وPoppler (مثبتة تلقائياً في Docker)

## التشغيل السريع (محلي)

```bash
cp .env.example .env
pip install -r requirements.txt
redis-server   # في نافذة منفصلة
celery -A tasks worker --loglevel=info   # في نافذة منفصلة
uvicorn app:app --reload
```

افتح: `http://localhost:8000`

## التشغيل بـ Docker

```bash
cp .env.example .env
docker compose up --build
```

## النشر على الإنتاج (pmi-edu.com)

راجع **[DEPLOY.md](DEPLOY.md)** للخطوات الكاملة: DNS، SSL، nginx، و `docker-compose.prod.yml`.

```bash
cp .env.production.example .env
docker compose -f docker-compose.prod.yml up -d --build
```

الخدمات المحلية (تطوير):
- التطبيق: `http://localhost:8000`
- MinIO: `http://localhost:9000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## مفاتيح API

ضع المفاتيح في `.env` على الخادم. عند تعبئتها هناك، تُخفى حقول الإدخال تلقائياً من الواجهة.

## التسجيل والمستخدمون

```env
ALLOW_REGISTRATION=false          # إغلاق التسجيل العام في الإنتاج
REGISTRATION_SECRET=رمز-سري       # اختياري: رمز دعوة للتسجيل
```

عند إغلاق التسجيل، أنشئ مستخدماً من سطر الأوامر:

```bash
python scripts/create_user.py --username admin
```

ثم عيّن في `.env`:

```env
ADMIN_USERNAMES=admin
```

## التخزين (S3/MinIO)

الملفات تُخزَّن في bucket **خاص** (بدون قراءة عامة). الروابط المُعادة للمتصفح هي **presigned URLs** مؤقتة.

```env
S3_PRESIGNED_EXPIRY=3600
```

## لوحة الإدارة

المستخدمون المدرجون في `ADMIN_USERNAMES` يرون زر **لوحة الإدارة** لإدارة المستخدمين والمشاريع وعرض الإحصائيات.

## الاختبارات

```bash
pytest tests/ -v
```

## البنية

| الملف | الوظيفة |
|-------|---------|
| `app.py` | واجهة FastAPI |
| `tasks.py` | مهام Celery |
| `utils.py` | PDF، ترجمة، TTS |
| `auth.py` | JWT |
| `storage.py` | MinIO/S3 |
| `models.py` | قاعدة البيانات |
