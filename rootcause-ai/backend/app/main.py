import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .models import models  # noqa: F401  (register tables)
from .api.routes import router

load_dotenv()
Base.metadata.create_all(engine)
app = FastAPI(title="RootCause AI", description="Don't just detect failures. Understand why they happen.", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
