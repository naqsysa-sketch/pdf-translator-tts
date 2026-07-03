# النشر على Vercel

## ملاحظة مهمة

Vercel مناسب كـ **عرض تجريبي**. للإنتاج الكامل (Celery، FFmpeg، ملفات كبيرة) استخدم Docker/VPS — راجع `DEPLOY.md`.

على Vercel:
- المهام تُنفَّذ **متزامنة** (`CELERY_TASK_ALWAYS_EAGER=true`)
- قاعدة البيانات: SQLite مؤقتة في `/tmp`
- بدون MinIO — الملفات الصوتية محلية مؤقتة
- حد زمني للطلب (~60 ثانية على Pro)

## ربط المشروع

1. ارفع الكود إلى GitHub
2. في [vercel.com](https://vercel.com) → **Add New Project** → اختر المستودع
3. Framework: **Other**
4. أضف متغيرات البيئة:

```env
SECRET_KEY=مفتاح-عشوائي-طويل
ALLOWED_ORIGINS=https://your-project.vercel.app
ALLOW_REGISTRATION=false
ADMIN_USERNAMES=admin
CELERY_TASK_ALWAYS_EAGER=true
DATABASE_URL=sqlite:////tmp/pdf_translator.db
GEMINI_API_KEY=...
```

5. Deploy

## ربط الدومين pmi-edu.com

1. Vercel Dashboard → المشروع → **Settings → Domains**
2. أضف: `pmi-edu.com` و `www.pmi-edu.com`
3. اتبع تعليمات DNS (A/CNAME) التي يعرضها Vercel
4. حدّث `ALLOWED_ORIGINS` في Environment Variables:

```env
ALLOWED_ORIGINS=https://pmi-edu.com,https://www.pmi-edu.com,https://pdf-translator-tts.vercel.app
```

5. أعد النشر: `npx vercel --prod`

## ربط GitHub (تحديث تلقائي عند كل push)

Vercel Dashboard → **Settings → Git** → Connect `naqsysa-sketch/pdf-translator-tts`

## بعد النشر

أنشئ مستخدم admin محلياً ثم استخدم التسجيل إن كان مفتوحاً، أو شغّل `create_user` على بيئة تدعم CLI.

للدومين `pmi-edu.com` على Vercel: **Settings → Domains → Add** `pmi-edu.com`
