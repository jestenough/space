#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

openssl req -x509 -nodes -days 1 -newkey rsa:2048 \
  -keyout "$tmp/key.pem" -out "$tmp/cert.pem" \
  -subj "/CN=localhost" >/dev/null 2>&1

sed \
  -e "s#/etc/letsencrypt/live/autophany.space/fullchain.pem#/tmp/nginx/cert.pem#" \
  -e "s#/etc/letsencrypt/live/autophany.space/privkey.pem#/tmp/nginx/key.pem#" \
  "$root/deploy/nginx/autophany.space.conf" > "$tmp/site.conf"

cat > "$tmp/nginx.conf" <<EOF
events {}
http {
  include /etc/nginx/mime.types;
  include /tmp/nginx/site.conf;
}
EOF

docker run --rm -v "$tmp:/tmp/nginx:ro" nginx:alpine nginx -t -c /tmp/nginx/nginx.conf
