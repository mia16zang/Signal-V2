from fastapi import FastAPI

from app.routes.analyze import router

app = FastAPI(
    title="Market Intelligence API"
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "running"
    }