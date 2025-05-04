from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Email Warmup API Test",
    description="A test API for warming up email accounts",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World from Email Warmup API!"}

if __name__ == "__main__":
    uvicorn.run("test_main:app", host="0.0.0.0", port=8000, reload=True) 