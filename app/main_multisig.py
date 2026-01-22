import fastapi
import bittensor as bt
import subprocess
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.core.config import settings
from app.constants import NETWORK
from app.services.wallets import wallets
from app.services.stake import stake_service
from app.services.auth import get_current_username
from utils.stake_list import get_stake_list
from utils.stake_list_v2 import get_stake_list_v2


app = fastapi.FastAPI()
app.include_router(router)


templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def read_root(request: fastapi.Request, username: str = Depends(get_current_username)):
    subtensor = stake_service.subtensor
    def get_balance_html():
        balance_html = ""
        for wallet_name in settings.WALLET_NAMES:
            _, delegator = wallets[wallet_name]
            balance = subtensor.get_balance(delegator)
            balance_html += f"""
                <div class="balance-container">
                    <div class="balance-title"><a target="_blank" href="/stake_list_v3?wallet_name={delegator}" style="text-decoration: none; color: inherit; cursor: pointer; text-decoration: underline;">{wallet_name}</a></div>
                    <div class="balance-amount">{balance} TAO</div>
                </div>
            """
        return balance_html

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, 
            "balance_html": get_balance_html(), 
            "wallet_names": settings.WALLET_NAMES,
            "delegators": settings.DELEGATORS,
        }
    )



@app.get("/stake_list")
def stake_list(wallet_name: str):
    result = subprocess.run(["btcli", "stake", "list", "--name", wallet_name, "--no-prompt"], capture_output=True, text=True)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{wallet_name} | Stake List</title>
    </head>
    <body>
        <pre>{result.stdout}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/stake_list_v2")
def stake_list_v2(wallet_name: str):
    subtensor = stake_service.subtensor
    stake_list = get_stake_list(subtensor, wallet_name)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{wallet_name} | Stake List</title>
    </head>
    <body>
        <pre>{stake_list}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/stake_list_v3")
def stake_list_v3(wallet_name: str):
    subtensor = stake_service.subtensor
    stake_list = get_stake_list_v2(subtensor, wallet_name)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{wallet_name} | Stake List</title>
    </head>
    <body>
        <pre>{stake_list}</pre>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/subnets")
def subnets_page(request: fastapi.Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse(
        "subnets_bubble.html",
        {"request": request}
    )

@app.get("/settings/tolerance_offset")
def get_tolerance_offset(username: str = Depends(get_current_username)):
    return {"tolerance_offset": settings.TOLERANCE_OFFSET}

@app.post("/settings/tolerance_offset")
def set_tolerance_offset(request: fastapi.Request, username: str = Depends(get_current_username)):
    tolerance_offset = request.query_params.get("tolerance_offset")
    if tolerance_offset is None:
        return {"error": "Tolerance offset is required"}
    # Allow both float and string values (e.g., "*1.1" for multiplication)
    tolerance_offset = tolerance_offset.strip()
    if tolerance_offset.startswith('*'):
        # Keep as string for multiplication mode
        settings.TOLERANCE_OFFSET = tolerance_offset
    else:
        # Convert to float for addition mode
        try:
            settings.TOLERANCE_OFFSET = float(tolerance_offset)
        except ValueError:
            return {"error": "Tolerance offset must be a valid number or multiplication (e.g., '*1.1')"}
    return {"success": True}
