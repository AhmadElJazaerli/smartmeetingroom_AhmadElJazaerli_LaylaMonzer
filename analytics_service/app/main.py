from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .routers import analytics

app = FastAPI(
    title="Analytics Service",
    description="Provides analytics, insights, and metrics for the Smart Meeting Room system",
    version="1.0.0"
)

# Add Prometheus metrics instrumentation
Instrumentator().instrument(app).expose(app)

app.include_router(analytics.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "analytics"}
