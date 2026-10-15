import json
import os
import traceback

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import engine

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(APP_DIR, "web")
DOCS_DIR = os.path.join(APP_DIR, "docs")

app = FastAPI(title="Quant Studio API")


@app.middleware("http")
async def no_cache_static(request, call_next):
    resp = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".css", ".js", ".html")):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


class RunBody(BaseModel):
    code: str
    params: dict | None = None
    settings: dict | None = None
    mode: str = "single"
    symbol: str = "BTC"
    symbols: list[str] | None = None
    weights: dict | None = None
    interval: str = "1d"
    start: str | None = None
    end: str | None = None
    source: str = "csv"
    refresh: bool = False
    use_hedge: bool = False


class StrategyBody(BaseModel):
    name: str
    code: str


class CodeBody(BaseModel):
    code: str


class OptBody(BaseModel):
    code: str
    params: dict | None = None
    settings: dict | None = None
    symbol: str = "BTC"
    interval: str = "1d"
    start: str | None = None
    end: str | None = None
    source: str = "csv"
    refresh: bool = False
    use_hedge: bool = False
    grid: dict
    metric: str = "sharpe"


@app.get("/api/meta")
def meta():
    return engine.assets_payload()


@app.post("/api/params")
def params(body: CodeBody):
    try:
        ns = engine.exec_custom(body.code)
        return {
            "ok": True,
            "param_defs": engine.param_defs(ns) or {},
            "has_generate": callable(ns.get("generate")),
        }
    except SyntaxError as e:
        return JSONResponse(status_code=400, content={
            "ok": False, "error": f"語法錯誤：{e.msg}（第 {e.lineno} 行）",
        })
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e) or e.__class__.__name__})


@app.post("/api/run")
def run(body: RunBody):
    def gen():
        try:
            for ev in engine.run_request_stream(body.model_dump()):
                yield json.dumps(ev, ensure_ascii=False, default=str) + "\n"
        except SyntaxError as e:
            yield json.dumps({"type": "error", "error": "程式碼語法錯誤", "detail": f"{e.msg} (line {e.lineno})"}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "error": str(e) or e.__class__.__name__, "detail": traceback.format_exc()}, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/optimize")
def optimize(body: OptBody):
    def gen():
        try:
            for ev in engine.optimize_stream(body.model_dump()):
                yield json.dumps(ev, ensure_ascii=False, default=str) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "error": str(e) or e.__class__.__name__, "detail": traceback.format_exc()}, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.get("/api/strategies")
def strategies():
    return {"names": engine.list_strategies()}


@app.get("/api/strategies/{name}")
def get_strategy(name: str):
    try:
        return {"name": name, "code": engine.read_strategy(name)}
    except Exception as e:
        return JSONResponse(status_code=404, content={"ok": False, "error": str(e)})


@app.post("/api/strategies")
def save_strategy(body: StrategyBody):
    try:
        saved = engine.save_strategy(body.name, body.code)
        return {"ok": True, "name": saved}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


@app.delete("/api/strategies/{name}")
def delete_strategy(name: str):
    try:
        return {"ok": True, "name": engine.delete_strategy(name)}
    except Exception as e:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(e)})


@app.get("/api/manual")
def manual():
    path = os.path.join(DOCS_DIR, "使用手冊.md")
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"ok": False, "error": "找不到手冊"})
    with open(path, "r", encoding="utf-8") as f:
        return {"markdown": f.read()}


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8050)
