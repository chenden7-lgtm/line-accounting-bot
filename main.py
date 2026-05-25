from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app = FastAPI()
@app.get("/")
def home():
    return HTMLResponse("<h1>小蛋診斷中：如果看到這行字，代表 Render 是活的！</h1><p>請告訴我你看到了這行字。</p>")
if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
