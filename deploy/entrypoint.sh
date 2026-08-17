#!/bin/sh
set -eu

envsubst '${NGINX_HSTS_HEADER} ${NGINX_CONTENT_SECURITY_POLICY}' \
  < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

exec "$@"
