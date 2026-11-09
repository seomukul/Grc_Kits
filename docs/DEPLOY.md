# Deploying GRCkits to a VPS

This guide sets up one Ubuntu 24.04 server (2 vCPU / 2–4 GB RAM is plenty to start). The stack is nginx → gunicorn → Django, with PostgreSQL on the same machine. Paid product files live in Cloudflare R2, and nightly backups go to R2 as well.

Replace `grckits.com` with your domain throughout.

## 0. Before you start (gather these)

| Item | Where |
|---|---|
| VPS with Ubuntu 24.04 + SSH access | Hetzner, DigitalOcean, Vultr, Contabo… |
| Domain DNS: `A` record for `grckits.com` and `www` → server IP | Your registrar or Cloudflare DNS |
| Stripe **live** secret + publishable key, live webhook secret | Stripe Dashboard → Developers |
| R2: account ID, a **files** bucket + token, a **backups** bucket + token | Cloudflare → R2 |
| SMTP credentials (Postmark, Amazon SES, Brevo, Resend…) | Your email provider; set SPF/DKIM for the domain |
| Optional: email-marketing API key, GA4 ID, Sentry DSN | — |

## 1. Server basics

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3.12-venv python3-dev build-essential libpq-dev \
  postgresql nginx certbot python3-certbot-nginx git awscli ufw
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
sudo adduser --system --group --home /srv/grckits grckits
sudo mkdir -p /srv/grckits/media /var/log/grckits /var/backups/grckits
sudo chown -R grckits:www-data /srv/grckits /var/log/grckits /var/backups/grckits
```

## 2. Database

```bash
sudo -u postgres psql -c "CREATE USER grckits WITH PASSWORD 'choose-a-long-random-password';"
sudo -u postgres psql -c "CREATE DATABASE grckits OWNER grckits;"
```

## 3. Code and environment

```bash
sudo -u grckits git clone https://github.com/seomukul/Grc_Kits.git /srv/grckits/app
sudo -u grckits python3.12 -m venv /srv/grckits/venv
sudo -u grckits /srv/grckits/venv/bin/pip install -r /srv/grckits/app/requirements.txt
sudo -u grckits cp /srv/grckits/app/.env.example /srv/grckits/app/.env
sudo -u grckits nano /srv/grckits/app/.env   # fill in (see below)
sudo chmod 600 /srv/grckits/app/.env
```

Key production values in `.env`:

```ini
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=grckits.com,www.grckits.com
CSRF_TRUSTED_ORIGINS=https://grckits.com,https://www.grckits.com
SITE_URL=https://grckits.com
DATABASE_URL=postgres://grckits:<db password>@localhost:5432/grckits
MEDIA_ROOT=/srv/grckits/media
STRIPE_SECRET_KEY=sk_live_…
STRIPE_PUBLISHABLE_KEY=pk_live_…
STRIPE_WEBHOOK_SECRET=whsec_…
R2_ACCOUNT_ID=…  R2_ACCESS_KEY_ID=…  R2_SECRET_ACCESS_KEY=…  R2_BUCKET_NAME=grckits-files
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=…  EMAIL_HOST_USER=…  EMAIL_HOST_PASSWORD=…
DEFAULT_FROM_EMAIL=GRCkits <hello@grckits.com>
ADMIN_EMAIL=you@example.com
ADMIN_2FA_REQUIRED=True
BACKUP_R2_BUCKET=grckits-backups  BACKUP_R2_ACCESS_KEY_ID=…  BACKUP_R2_SECRET_ACCESS_KEY=…
```

## 4. First build

```bash
cd /srv/grckits/app
sudo -u grckits bash -c 'export DJANGO_SETTINGS_MODULE=config.settings.prod
  /srv/grckits/venv/bin/python manage.py migrate
  /srv/grckits/venv/bin/python manage.py tailwind build
  /srv/grckits/venv/bin/python manage.py collectstatic --noinput
  /srv/grckits/venv/bin/python manage.py seed_content
  /srv/grckits/venv/bin/python manage.py check --deploy
  /srv/grckits/venv/bin/python manage.py createsuperuser'
```

Don't run `seed_demo` or `seed_sales` in production.

## 5. gunicorn, nginx, HTTPS

```bash
sudo cp deploy/systemd/grckits.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now grckits

sudo cp deploy/nginx/grckits.conf /etc/nginx/sites-available/grckits
# First run only: comment out the two "listen 443" server blocks, then:
sudo ln -s /etc/nginx/sites-available/grckits /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d grckits.com -d www.grckits.com
# Restore the 443 blocks from deploy/nginx/grckits.conf, then:
sudo nginx -t && sudo systemctl reload nginx
```

Let deploys reload gunicorn without a password:

```bash
echo 'grckits ALL=NOPASSWD: /bin/systemctl reload grckits' | sudo tee /etc/sudoers.d/grckits
```

## 6. Scheduled jobs and backups

```bash
sudo cp deploy/cron/grckits /etc/cron.d/grckits
sudo -u grckits /srv/grckits/app/deploy/backup.sh   # test once
```

On the backups bucket in R2, add a lifecycle rule that deletes objects after 90 days. Test a restore at least once:
`pg_restore --clean --no-owner -d grckits db-YYYYMMDD-HHMM.dump`.

## 7. Third-party setup

- **Stripe:** add the webhook endpoint `https://grckits.com/checkout/webhook/stripe/` with the 7 events listed in the README. Enable Apple Pay, Google Pay and Link, and verify the domain for Apple Pay. Turn on customer emails if you want Stripe receipts as well.
- **R2 CORS** on the files bucket: allow `PUT` from `https://grckits.com` (see the README).
- **Email:** add SPF, DKIM and DMARC DNS records from your SMTP provider. Send a test with `python manage.py sendtestemail you@example.com`.
- **Google:** add the GA4 ID and the Search Console verification token in *Admin → Site settings*, then submit `https://grckits.com/sitemap.xml` in Search Console.
- **Uptime:** point UptimeRobot or Better Stack at `https://grckits.com/health/` (expect 200, checked every 5 minutes).

## 8. Updating

```bash
sudo -u grckits /srv/grckits/app/deploy/deploy.sh
```

## Launch checklist

- [ ] `check --deploy` is clean; `DEBUG=False`
- [ ] Owner logged in to `/admin/` and set up 2FA (saved the backup codes)
- [ ] Real products created with files uploaded to R2 and test-downloaded
- [ ] Stripe live: one real purchase (refund it afterwards) delivered the email and download
- [ ] About page, contact email, social links and lead magnet filled in (Site settings)
- [ ] Privacy, Terms, Refund and License pages reviewed by a lawyer
- [ ] GA4 and Search Console connected; sitemap submitted
- [ ] Backups running and a restore tested; uptime monitor active
- [ ] DNS: `www` redirects to the apex domain; HTTPS grade A at ssllabs.com
