FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . /app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
CMD ["uvicorn", "services.rooms.app:app", "--host", "0.0.0.0", "--port", "8002"]
