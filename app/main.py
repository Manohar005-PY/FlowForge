from fastapi import FastAPI
from app.api.routes.job import job as jobrouter

app = FastAPI()

app.include_router(jobrouter)