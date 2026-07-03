# نشر المشروع على pmi-edu.com

## البنية المقترحة

| الدومين | الاستخدام |
|---------|-----------|
| `https://pmi-edu.com` | التطبيق الرئيسي (واجهة + API) |
| `https://www.pmi-edu.com` | يُحوَّل تلقائياً إلى `pmi-edu.com` |
| `https://storage.pmi-edu.com` | MinIO خاص — روابط الصوت المؤقتة (presigned) |

## 1) إعداد DNS

في لوحة تحكم الدومين (Registrar / Cloudflare)، أضف:

| النوع | الاسم | القيمة |
|-------|-------|--------|
| A | `@` | `IP_السيرفر` |
| A | `www` | `IP_السيرفر` |
| A | `storage` | `IP_السيرفر` |

انتظر انتشار DNS (5–30 دقيقة عادةً).

## 2) تجهيز السيرفر (Ubuntu VPS)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
# أعد تسجيل الدخول
```

## 3) رفع المشروع

```bash
git clone <repo-url> pdf-translator-tts
cd pdf-translator-tts
cp .env.production.example .env
nano .env   # عبّئ SECRET_KEY, POSTGRES_PASSWORD, مفاتيح API, MinIO
```

## 4) شهادة SSL (Let's Encrypt) — أول مرة

شغّل nginx مؤقتاً بدون SSL أو استخدم certbot standalone:

```bash
# أوقف أي خدمة على المنفذ 80
docker compose -f docker-compose.prod.yml up -d web redis db minio

docker run --rm -it \
  -v pdf-translator-tts_certbot_www:/var/www/certbot \
  -v pdf-translator-tts_certbot_certs:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d pmi-edu.com -d www.pmi-edu.com -d storage.pmi-edu.com \
  --email you@pmi-edu.com --agree-tos --no-eff-email
```

## 5) تشغيل الإنتاج

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 6) إنشاء حساب المسؤول

```bash
docker compose -f docker-compose.prod.yml exec web python scripts/create_user.py --username admin
```

تأكد أن `.env` يحتوي:

```env
ADMIN_USERNAMES=admin
ALLOW_REGISTRATION=false
```

## 7) التحقق

- افتح: https://pmi-edu.com
- سجّل الدخول بحساب admin
- ارفع PDF صغير وجرّب الترجمة والصوت
- Health: https://pmi-edu.com/api/health

## ملاحظات مهمة

1. **لا تفتح** منافذ PostgreSQL / Redis / MinIO للعامة — فقط 80 و 443 عبر nginx.
2. روابط MP3 تُولَّد عبر `S3_PUBLIC_ENDPOINT_URL=https://storage.pmi-edu.com`.
3. إذا استخدمت **Cloudflare**، فعّل SSL mode = Full (strict) بعد تثبيت الشهادة.
4. لتطبيق فرعي بدل الجذر (مثلاً `pdf.pmi-edu.com`)، عدّل ملفات `deploy/nginx/conf.d/` و `ALLOWED_ORIGINS`.

## تحديث التطبيق

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
