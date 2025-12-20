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

WALLET_NAME = "fantacy"

@app.get("/")
def read_root(request: fastapi.Request, wallet_name: str = WALLET_NAME):
    hotkeys = get_hotkeys(wallet_name)
    return templates.TemplateResponse(
        "index_reg.html",
        {"request": request, "wallet_names":[WALLET_NAME], "hotkeys": hotkeys, "wallet_name": wallet_name}
    )

@app.get("/wallet_list")
def wallet_list_page(request: fastapi.Request, wallet_name: str):
    hotkeys = get_hotkeys(wallet_name)
    return templates.TemplateResponse(
        "index_reg.html",
        {"request": request, "wallet_names":[WALLET_NAME], "hotkeys": hotkeys, "wallet_name": wallet_name}
    )

@app.get("/health")
def health():
    return {"status": "ok"}

