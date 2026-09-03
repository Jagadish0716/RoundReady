FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY libs ./libs
RUN pip install --prefix=/install .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/install/lib/python3.12/site-packages:/app/libs \
    PATH=/install/bin:$PATH

WORKDIR /app
COPY --from=builder /install /install
COPY services/booking-service/app ./app
COPY services/booking-service/alembic ./alembic
COPY services/booking-service/alembic.ini ./alembic.ini

RUN addgroup --system app && adduser --system --ingroup app app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
