FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 lab \
    && useradd --uid 10001 --gid lab --no-create-home lab \
    && mkdir /app/data \
    && chown lab:lab /app/data
COPY --chown=lab:lab app ./app
COPY --chown=lab:lab examples ./examples
USER lab
ENV DATABASE_PATH=/app/data/assets.db
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
