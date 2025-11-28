FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . /app
COPY services/bookings/rabbitmq_test.py /app/services/bookings/rabbitmq_test.py
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
CMD ["uvicorn", "services.bookings.app:app", "--host", "0.0.0.0", "--port", "8003"]
