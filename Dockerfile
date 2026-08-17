# syntax=docker/dockerfile:1
FROM node:22-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS python-build
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel --outdir /wheels \
    && pip wheel --no-cache-dir --wheel-dir /wheels /wheels/roleplay_catalogue-*.whl

FROM python:3.12-slim AS runtime
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    RC_APP_HOST=127.0.0.1 \
    RC_APP_PORT=9798 \
    RC_API_PREFIX="" \
    NGINX_HSTS_HEADER="" \
    NGINX_CONTENT_SECURITY_POLICY="default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
RUN apt-get update \
    && apt-get install --no-install-recommends -y gettext-base nginx supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv "$VIRTUAL_ENV"
COPY --from=python-build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels roleplay-catalogue \
    && rm -rf /wheels
COPY --from=frontend-build /build/frontend/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/nginx.conf.template
COPY deploy/supervisord.conf /etc/supervisor/conf.d/roleplay-catalogue.conf
COPY deploy/entrypoint.sh /usr/local/bin/roleplay-catalogue-entrypoint
RUN chmod 755 /usr/local/bin/roleplay-catalogue-entrypoint
EXPOSE 8080
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/local/bin/roleplay-catalogue-entrypoint"]
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
