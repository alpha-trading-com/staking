import fastapi
import bittensor as bt
import subprocess
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


from app.api.routes_reg import router
from app.services.reg import get_hotkeys

app = fastapi.FastAPI()



templates = Jinja2Templates(directory="app/templates")

app.include_router(router)


@app.get("/")
def read_root(request: fastapi.Request):
    hotkeys = get_hotkeys("tck")
    return templates.TemplateResponse(
        "index_reg.html",
        {"request": request, "wallet_names":["tck"], "hotkeys": hotkeys}
    )

@app.get("/health")
def health():
    return {"status": "ok"}

