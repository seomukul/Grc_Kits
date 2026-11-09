#!/usr/bin/env bash
# Nightly backup: PostgreSQL dump + public media, kept locally and copied to a private R2 bucket.
# Paid product files already live in R2, so they're not included here.
#
# Needs: awscli (apt install awscli) and these in /srv/grckits/app/.env:
#   DATABASE_URL, R2_ACCOUNT_ID, BACKUP_R2_BUCKET, BACKUP_R2_ACCESS_KEY_ID, BACKUP_R2_SECRET_ACCESS_KEY
set -euo pipefail

APP=/srv/grckits/app
DEST=/var/backups/grckits
KEEP_DAYS=14
STAMP=$(date -u +%Y%m%d-%H%M)

set -a; source "$APP/.env"; set +a
mkdir -p "$DEST"

pg_dump --no-owner --format=custom "$DATABASE_URL" > "$DEST/db-$STAMP.dump"
tar -czf "$DEST/media-$STAMP.tar.gz" -C /srv/grckits media 2>/dev/null || true

# Off-site copy (configure a lifecycle rule on the bucket to expire old objects, e.g. after 90 days).
if [[ -n "${BACKUP_R2_BUCKET:-}" ]]; then
  export AWS_ACCESS_KEY_ID="$BACKUP_R2_ACCESS_KEY_ID" AWS_SECRET_ACCESS_KEY="$BACKUP_R2_SECRET_ACCESS_KEY"
  ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
  for f in "$DEST/db-$STAMP.dump" "$DEST/media-$STAMP.tar.gz"; do
    [[ -f "$f" ]] && aws s3 cp "$f" "s3://$BACKUP_R2_BUCKET/$(basename "$f")" --endpoint-url "$ENDPOINT" --only-show-errors
  done
fi

find "$DEST" -type f -mtime +"$KEEP_DAYS" -delete
echo "$(date -u) backup ok: db-$STAMP.dump"
