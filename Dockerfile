FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /srv/adjuntos && useradd --create-home appuser && chown -R appuser /srv
USER appuser

ENV FLASK_APP=app:create_app
EXPOSE 5000
CMD ["sh", "-c", "flask init-db && ([ \"$SEED_DEMO\" = \"1\" ] && flask seed-demo || true) && waitress-serve --host=0.0.0.0 --port=5000 --call app:create_app"]
