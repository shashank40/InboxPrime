import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import users, emails, warmup, dashboard, auth
from app.db.database import create_tables
from app.core.scheduler import start_scheduler

app = FastAPI(
    title="Email Warmup API",
    description="A robust API for warming up email accounts to improve deliverability",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(emails.router, prefix="/api/emails", tags=["Email Accounts"])
app.include_router(warmup.router, prefix="/api/warmup", tags=["Warmup"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

@app.on_event("startup")
async def startup_event():
    create_tables()
    # Start the scheduler
    start_scheduler()

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to Email Warmup API. Go to /docs for documentation."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True) 