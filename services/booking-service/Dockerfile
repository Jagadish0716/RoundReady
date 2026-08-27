FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/libs

WORKDIR /app
COPY pyproject.toml README.md ./
COPY libs ./libs
RUN pip install --no-cache-dir .
COPY services/booking-service/app ./app
COPY services/booking-service/alembic ./alembic
COPY services/booking-service/alembic.ini ./alembic.ini

RUN addgroup --system app && adduser --system --ingroup app app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
