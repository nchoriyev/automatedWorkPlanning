# MTMS (Mobiuz) — serverga deploy qilish

Bu qo‘llanma loyihani **Ubuntu 22.04 LTS** (yoki yaqin versiya) serverda **PostgreSQL**, **Gunicorn** va **Nginx** bilan ishga tushirish uchun yozilgan.

---

## Xavfsizlik ogohlantirishlari

- Quyida berilgan **PostgreSQL paroli va boshqa maxfiy ma’lumotlar** faqat sizning serveringiz uchun mo‘ljallangan. Agar bu repozitoriy faqat jamoa ichida bo‘lsa ham, kelajakda **parolni almashtirish** va `.env` faylni **Git ga commit qilmaslik** tavsiya etiladi (loyihada `.env` allaqachon `.gitignore` da).
- Ishga tushirishdan oldin yangi **`DJANGO_SECRET_KEY`** generate qiling (`openssl` misoli quyida).

---

## Berilgan ma’lumotlar (sizning talabingiz bo‘yicha)

| Parametr | Qiymat |
|----------|--------|
| Domen | `mobiuz-rmpo.uz` |
| Server IP | `16.171.36.156` |
| PostgreSQL DB nomi | `mobiuz` |
| PostgreSQL user | `sardor` |
| PostgreSQL parol | `Sardor2003` |

**DNS:** domen uchun **A** yozuvi `mobiuz-rmpo.uz` → `16.171.36.156` bo‘lishi kerak (agar `www` ishlatilsa, alohida **A** yoki **CNAME**).

---

## 1. Server paketlari

SSH orqali serverga kiring va yangilang:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12-venv python3-pip python3-dev build-essential \
  nginx postgresql postgresql-contrib git curl certbot python3-certbot-nginx
```

> Agar `python3.12-venv` topilmasa: `sudo apt install -y python3-venv` va keyingi qadamda `python3` versiyasiga mos venv ishlating.

---

## 2. PostgreSQL — foydalanuvchi va baza

```bash
sudo -u postgres psql <<'SQL'
CREATE USER sardor WITH PASSWORD 'Sardor2003';
CREATE DATABASE mobiuz OWNER sardor;
GRANT ALL PRIVILEGES ON DATABASE mobiuz TO sardor;
ALTER DATABASE mobiuz OWNER TO sardor;
SQL
```

PostgreSQL 15+ da schema huquqlari kerak bo‘lishi mumkin:

```bash
sudo -u postgres psql -d mobiuz -c 'GRANT ALL ON SCHEMA public TO sardor;'
```

Ulanish satri (Django `DATABASE_URL`):

```text
postgresql://sardor:Sardor2003@127.0.0.1:5432/mobiuz
```

---

## 3. Loyiha katalogi va virtual muhit

Misol yo‘l: `/srv/mobiuz_app` (ixtiyoriy, lekin keyingi systemd/Nginx misollarida shu yo‘l ishlatiladi).

```bash
sudo mkdir -p /srv/mobiuz_app
sudo chown $USER:$USER /srv/mobiuz_app
```

Loyiha fayllarini joylashtiring:

- **Git** orqali: repozitoriyani klonlang va shu katalogga chiqaring; yoki  
- **Mahalliy mashinadan** `scp` / `rsync` bilan yuklang.

Keyin:

```bash
cd /srv/mobiuz_app
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. `.env` — production sozlamalari

`/srv/mobiuz_app/.env` faylini yarating (faqat serverda, Git ga emas):

```bash
cd /srv/mobiuz_app
nano .env
```

Minimal tarkib (SECRET_KEY ni almashtiring):

```env
DJANGO_SECRET_KEY=BUNI_ALMASHTIR_OPENSSL_RAND_BILAN
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=mobiuz-rmpo.uz,www.mobiuz-rmpo.uz,16.171.36.156,127.0.0.1

DJANGO_CSRF_TRUSTED_ORIGINS=https://mobiuz-rmpo.uz,https://www.mobiuz-rmpo.uz

DJANGO_BEHIND_PROXY=true

DATABASE_URL=postgresql://sardor:Sardor2003@127.0.0.1:5432/mobiuz
```

**HTTPS yoqilgandan keyin** (Certbotdan so‘ng) quyidagilarni qo‘shing yoki `true` qiling:

```env
DJANGO_SECURE_COOKIES=true
DJANGO_SECURE_SSL_REDIRECT=true
```

**Yangi kalit:**

```bash
openssl rand -base64 48
```

`.env` huquqlari:

```bash
chmod 600 /srv/mobiuz_app/.env
```

---

## 5. Migratsiya, statik fayllar, superuser

```bash
cd /srv/mobiuz_app
source .venv/bin/activate

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Tarjimalar kompilyatsiyasi (agar `locale/` dan foydalansangiz):

```bash
python manage.py compilemessages
```

---

## 6. Media katalogi

Yuklangan fayllar `MEDIA_ROOT` (loyihada `media/`) ga yoziladi.

```bash
mkdir -p /srv/mobiuz_app/media
```

To‘liq huquqlar **7-bobda** `chown -R www-data` bilan beriladi.

---

## 7. Gunicorn — systemd servis

Systemd `RuntimeDirectory=gunicorn` `/run/gunicorn/` ni yaratadi — qo‘lda `mkdir` shart emas.

`/etc/systemd/system/mobiuz-gunicorn.service`:

```ini
[Unit]
Description=Mobiuz MTMS Gunicorn
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=/srv/mobiuz_app
Environment="PATH=/srv/mobiuz_app/.venv/bin"
ExecStart=/srv/mobiuz_app/.venv/bin/gunicorn \
  --bind unix:/run/gunicorn/mobiuz.sock \
  --workers 3 \
  --timeout 120 \
  mtms.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Loyiha katalogiga **www-data** o‘qishi va yozishi kerak (venv, kod, `.env`, migratsiyalar paytida yozuvlar bo‘lmasa ham media/static uchun qulay):

```bash
sudo chown -R www-data:www-data /srv/mobiuz_app
```

Keyingi `git pull` uchun `sudo` orqali ishlab, keyin yana `chown` qilish yoki alohida deploy foydalanuvchi + guruh huquqlari sozlashingiz mumkin.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mobiuz-gunicorn
sudo systemctl status mobiuz-gunicorn
```

---

## 8. Nginx

`/etc/nginx/sites-available/mobiuz-rmpo`:

```nginx
upstream mobiuz_app {
    server unix:/run/gunicorn/mobiuz.sock fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name mobiuz-rmpo.uz www.mobiuz-rmpo.uz;

    client_max_body_size 52M;

    location /static/ {
        alias /srv/mobiuz_app/staticfiles/;
    }

    location /media/ {
        alias /srv/mobiuz_app/media/;
    }

    location / {
        proxy_pass http://mobiuz_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Faollashtirish:

```bash
sudo ln -sf /etc/nginx/sites-available/mobiuz-rmpo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**HTTPS (Let’s Encrypt):**

```bash
sudo certbot --nginx -d mobiuz-rmpo.uz -d www.mobiuz-rmpo.uz
```

Shundan keyin `.env` ga `DJANGO_SECURE_COOKIES` va `DJANGO_SECURE_SSL_REDIRECT` qo‘shib, servisni qayta ishga tushiring:

```bash
sudo systemctl restart mobiuz-gunicorn
```

---

## 9. Tekshiruv ro‘yxati

- `https://mobiuz-rmpo.uz/` ochiladi.
- Admin: `https://mobiuz-rmpo.uz/admin/`
- Statika 404 bo‘lmasin — `collectstatic` va `alias /static/` yo‘li to‘g‘ri bo‘lsin.
- Vazifa ilovalari/upload: `media/` nginx orqali berilyapti (`DEBUG=false` da Django media bermaydi).

---

## 10. Yangilanishlar (keyingi deploylar)

```bash
cd /srv/mobiuz_app
source .venv/bin/activate
git pull   # yoki yangi arxivni chiqarish
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart mobiuz-gunicorn
```

---

## 11. Firewall (ixtiyoriy, tavsiya etiladi)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## Loyihada qilingan tayyorlashlar (qisqa)

- `requirements.txt` ga **gunicorn** qo‘shildi.
- `mtms/settings.py`: **`DJANGO_CSRF_TRUSTED_ORIGINS`**, **proxy** (`DJANGO_BEHIND_PROXY`), **`DEBUG=false`** uchun **xavfsiz cookie / SSL redirect** (`.env` orqali).
- `.env.example` production uchun izoh bilan yangilandi.

Savollar bo‘lsa (masalan, Redis, S3, boshqa OS), shu hujjat asosida kengaytirish mumkin.
