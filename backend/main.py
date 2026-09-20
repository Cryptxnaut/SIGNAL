import asyncio
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import schema_inference
import data_quality
import llm_client
import stats_pipeline
import model_builder
import stress_tester
import finding_ranker
import ble_listener
import domain_detector

app = FastAPI(title="SIGNAL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store
datasets: Dict[str, dict] = {}


# ─── Models ────────────────────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    dataset_id: str
    intent: str
    depth: str = "deep"  # "quick" | "deep" | "stress"


class ConsultantRequest(BaseModel):
    dataset_id: str
    message: str
    history: List[dict] = []


class LoadUrlRequest(BaseModel):
    url: str
    name: str = "dataset"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _clean_model_result(m: dict) -> dict:
    """Remove internal keys before sending to client."""
    return {k: v for k, v in m.items() if not k.startswith("_")}


def _df_preview(df: pd.DataFrame) -> list:
    return df.head(5).where(pd.notnull(df), None).to_dict(orient="records")


def _store_dataset(df: pd.DataFrame, name: str, source: str = "UPLOADED") -> dict:
    """Create and store a dataset entry, return the response dict."""
    dataset_id = str(uuid.uuid4())
    datasets[dataset_id] = {
        "meta": {
            "name": name,
            "rows": len(df),
            "columns": len(df.columns),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "quality_score": None,
        },
        "df": df,
        "schema": {},
        "quality": {},
        "findings": [],
        "model": {},
        "stress_test": {},
        "report": {},
    }
    return {
        "dataset_id": dataset_id,
        "name": name,
        "rows": len(df),
        "columns": len(df.columns),
        "preview": _df_preview(df),
    }


# ─── In-memory GameForge event store ───────────────────────────────────────────
gameforge_events: List[dict] = []


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    ollama_online = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            ollama_online = resp.status_code == 200
    except Exception:
        pass
    return {"status": "ok", "ollama_online": ollama_online}


@app.get("/api/hardware/status")
async def hardware_status():
    return await ble_listener.get_hardware_status()


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "dataset"

    # Large file warning threshold: 100MB
    LARGE_FILE_BYTES = 100 * 1024 * 1024
    MAX_SAMPLE_ROWS = 50_000

    try:
        if filename.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    # Sample large files to avoid memory/performance issues
    if len(content) > LARGE_FILE_BYTES and len(df) > MAX_SAMPLE_ROWS:
        df = df.sample(MAX_SAMPLE_ROWS, random_state=42).reset_index(drop=True)

    return _store_dataset(df, filename, source="UPLOADED")


@app.post("/api/load_url")
async def load_url(req: LoadUrlRequest):
    """Download a CSV or Parquet file from a URL and register it as a dataset."""
    MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024  # 500MB
    MAX_SAMPLE_ROWS = 50_000

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()
            content = resp.content
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download URL: HTTP {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download URL: {e}")

    if len(content) > MAX_DOWNLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large: {len(content) // (1024*1024)}MB exceeds 500MB limit")

    name = req.name or req.url.split("/")[-1] or "dataset"

    try:
        url_lower = req.url.lower().split("?")[0]
        if url_lower.endswith(".parquet"):
            df = pd.read_parquet(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse downloaded file: {e}")

    # Sample large files
    if len(df) > MAX_SAMPLE_ROWS:
        df = df.sample(MAX_SAMPLE_ROWS, random_state=42).reset_index(drop=True)

    return _store_dataset(df, name, source="URL")


@app.get("/api/dataset/{dataset_id}")
async def get_dataset(dataset_id: str):
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    entry = datasets[dataset_id]
    return {
        "dataset_id": dataset_id,
        "meta": entry["meta"],
        "schema": entry["schema"],
        "quality": entry["quality"],
        "preview": _df_preview(entry["df"]),
    }


@app.get("/api/findings/{dataset_id}")
async def get_findings(dataset_id: str):
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"findings": datasets[dataset_id]["findings"]}


@app.get("/api/model/{dataset_id}")
async def get_model(dataset_id: str):
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _clean_model_result(datasets[dataset_id]["model"])


@app.get("/api/stress/{dataset_id}")
async def get_stress(dataset_id: str):
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return datasets[dataset_id]["stress_test"]


@app.get("/api/report/{dataset_id}")
async def get_report(dataset_id: str):
    if dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return datasets[dataset_id]["report"]


@app.post("/api/analyse")
async def analyse(req: AnalyseRequest):
    if req.dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")

    async def generate_events():
        entry = datasets[req.dataset_id]
        df: pd.DataFrame = entry["df"]
        llm_online = True

        # Stage 1: Schema inference
        yield json.dumps({
            "stage": "schema",
            "message": "Inferring schema...",
            "progress": 5,
        }) + "\n"
        await asyncio.sleep(0)

        schema = schema_inference.infer_schema(df)
        entry["schema"] = schema

        # Detect domain
        domain = domain_detector.detect_domain(schema, req.intent)

        yield json.dumps({
            "stage": "schema",
            "message": f"Schema inferred — {schema['n_columns']} columns, {schema['n_time_series']} time-series detected, domain: {domain}",
            "progress": 10,
            "domain": domain,
        }) + "\n"
        await asyncio.sleep(0)

        # Small dataset warning
        if len(df) < 50:
            yield json.dumps({
                "stage": "warning",
                "message": f"Dataset has only {len(df)} rows — statistical results may be unreliable.",
                "progress": 10,
            }) + "\n"
            await asyncio.sleep(0)

        # Stage 2: Data quality
        yield json.dumps({
            "stage": "quality",
            "message": "Scoring data quality...",
            "progress": 15,
        }) + "\n"
        await asyncio.sleep(0)

        quality = data_quality.score_quality(df, schema)
        entry["quality"] = quality
        entry["meta"]["quality_score"] = quality["overall_quality"]

        quality_pct = int(quality["overall_quality"] * 100)
        yield json.dumps({
            "stage": "quality",
            "message": f"Data quality scored — {quality_pct}% overall",
            "progress": 20,
        }) + "\n"
        await asyncio.sleep(0)

        # Stage 3: LLM hypotheses
        yield json.dumps({
            "stage": "hypotheses",
            "message": "Generating analysis plan via LLM...",
            "progress": 25,
        }) + "\n"
        await asyncio.sleep(0)

        try:
            hypotheses = await llm_client.generate_hypotheses(schema, req.intent, domain=domain)
        except llm_client.LLMOfflineError:
            llm_online = False
            hypotheses = llm_client._fallback_hypotheses(schema)

        n_hyp = len(hypotheses)
        yield json.dumps({
            "stage": "hypotheses",
            "message": f"Analysis plan generated — {n_hyp} hypotheses",
            "progress": 30,
        }) + "\n"
        await asyncio.sleep(0)

        # Stage 4+5: Stats and model building in PARALLEL
        yield json.dumps({
            "stage": "stats",
            "message": "Running statistical tests and training model in parallel...",
            "progress": 40,
        }) + "\n"
        await asyncio.sleep(0)

        loop = asyncio.get_event_loop()
        stats_task = loop.run_in_executor(None, stats_pipeline.run_stats, df, hypotheses, schema)
        model_task = loop.run_in_executor(None, model_builder.build_model, df, schema, req.intent, req.depth)

        stats_results, model_result = await asyncio.gather(stats_task, model_task)

        entry["model"] = model_result

        yield json.dumps({
            "stage": "stats",
            "message": f"Statistical analysis complete — {len(stats_results)} tests run",
            "progress": 55,
        }) + "\n"
        await asyncio.sleep(0)

        metric_name = model_result.get("metric_name", "R²")
        metric_val = model_result.get("metric_value", 0.0)
        yield json.dumps({
            "stage": "model",
            "message": f"Model trained — {metric_name}: {metric_val:.3f}",
            "progress": 70,
        }) + "\n"
        await asyncio.sleep(0)

        # Stage 6: Stress test (skip if quick)
        stress_result = {}
        if req.depth in ("deep", "stress"):
            yield json.dumps({
                "stage": "stress",
                "message": "Running adversarial stress tests...",
                "progress": 75,
            }) + "\n"
            await asyncio.sleep(0)

            stress_result = stress_tester.run_stress_test(df, model_result)
            entry["stress_test"] = stress_result

            yield json.dumps({
                "stage": "stress",
                "message": f"Stress test complete — {len(stress_result.get('edge_cases', []))} critical edge cases found",
                "progress": 85,
            }) + "\n"
            await asyncio.sleep(0)
        else:
            yield json.dumps({
                "stage": "stress",
                "message": "Stress test skipped (quick scan mode)",
                "progress": 85,
            }) + "\n"
            await asyncio.sleep(0)

        # Stage 7: Rank findings + LLM explanations (batch)
        yield json.dumps({
            "stage": "findings",
            "message": "Ranking findings...",
            "progress": 90,
        }) + "\n"
        await asyncio.sleep(0)

        ranked = finding_ranker.rank_findings(stats_results)

        # Batch LLM explanations — single call instead of one per finding
        if llm_online:
            try:
                explanations = await llm_client.explain_findings_batch(ranked, req.intent, domain=domain)
                for finding in ranked:
                    name = finding.get("name", "")
                    finding["explanation"] = explanations.get(name, finding.get("name", ""))
            except Exception:
                for finding in ranked:
                    finding["explanation"] = finding.get("name", "")
        else:
            for finding in ranked:
                finding["explanation"] = finding.get("name", "")

        entry["findings"] = ranked

        n_significant = len([
            f for f in ranked
            if f.get("significance_score", 0) > 0.5
        ])

        yield json.dumps({
            "stage": "findings",
            "message": f"Findings ranked — {n_significant} significant signals identified",
            "progress": 95,
        }) + "\n"
        await asyncio.sleep(0)

        # Stage 8: Report compilation
        report = {
            "dataset_id": req.dataset_id,
            "dataset_name": entry["meta"]["name"],
            "intent": req.intent,
            "depth": req.depth,
            "domain": domain,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_summary": {
                "n_rows": schema["n_rows"],
                "n_columns": schema["n_columns"],
                "n_time_series": schema["n_time_series"],
            },
            "quality": quality,
            "findings": ranked[:5],
            "model": _clean_model_result(model_result),
            "stress_test": stress_result,
            "llm_online": llm_online,
        }

        # Executive summary
        if llm_online:
            try:
                summary = await llm_client.executive_summary(report)
                report["executive_summary"] = summary
            except Exception:
                report["executive_summary"] = (
                    f"Analysis of {entry['meta']['name']} identified {len(ranked)} findings. "
                    f"Data quality: {quality_pct}%. "
                    f"Model {metric_name}: {metric_val:.3f}."
                )
        else:
            report["executive_summary"] = (
                f"Analysis of {entry['meta']['name']} identified {len(ranked)} findings. "
                f"Data quality: {quality_pct}%. "
                f"Model {metric_name}: {metric_val:.3f}."
            )

        entry["report"] = report

        clean_model = _clean_model_result(model_result)

        yield json.dumps({
            "stage": "complete",
            "message": "Analysis complete",
            "progress": 100,
            "report_ready": True,
            "findings": ranked,
            "model": clean_model,
            "extra_metrics": model_result.get("extra_metrics", {}),
            "stress_test": stress_result,
            "quality": quality,
            "domain": domain,
        }) + "\n"

    return StreamingResponse(
        generate_events(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no"},
    )


@app.post("/api/consultant")
async def consultant(req: ConsultantRequest):
    if req.dataset_id not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")

    entry = datasets[req.dataset_id]
    context = {
        "schema": entry.get("schema", {}),
        "findings": entry.get("findings", []),
        "model": _clean_model_result(entry.get("model", {})),
        "quality": entry.get("quality", {}),
    }

    async def sse_stream():
        try:
            async for token in llm_client.stream_consultant(
                req.message, req.history, context
            ):
                yield f"data: {json.dumps(token)}\n\n"
        except llm_client.LLMOfflineError:
            yield f"data: {json.dumps('LLM service is offline. Please start Ollama.')}\n\n"
        except Exception as e:
            yield f"data: {json.dumps(f'Error: {str(e)}')}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/api/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            queue = await ble_listener.get_live_data_queue()
            if queue is not None:
                try:
                    data = queue.get_nowait()
                    await websocket.send_json({"type": "data", "payload": data})
                except Exception:
                    await websocket.send_json({"type": "ping"})
            else:
                await websocket.send_json({"type": "ping"})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ─── GameForge Integration ──────────────────────────────────────────────────────

class GameForgeIngestRequest(BaseModel):
    events: List[dict]


@app.post("/api/gameforge/events")
async def gameforge_ingest(req: GameForgeIngestRequest):
    """Receive batched analytics events from GameForge."""
    gameforge_events.extend(req.events)
    # Keep max 50k events in memory
    if len(gameforge_events) > 50000:
        del gameforge_events[:-50000]
    return {"received": len(req.events), "total": len(gameforge_events)}


@app.get("/api/gameforge/export")
async def gameforge_export():
    """Export all GameForge events as CSV for download / upload to SIGNAL."""
    if not gameforge_events:
        raise HTTPException(status_code=404, detail="No GameForge events recorded yet.")
    columns = ["session_id", "world_id", "difficulty", "event_type", "timestamp",
               "time_in_session_s", "value1", "value2", "value3"]
    rows = [columns]
    for e in gameforge_events:
        rows.append([str(e.get(c, "")) for c in columns])
    csv_text = "\n".join(",".join(f'"{v.replace(chr(34), chr(34)*2)}"' for v in row) for row in rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gameforge-events.csv"},
    )


@app.post("/api/gameforge/dataset")
async def gameforge_create_dataset():
    """Create a SIGNAL dataset directly from buffered GameForge events."""
    if not gameforge_events:
        raise HTTPException(status_code=404, detail="No GameForge events recorded yet.")
    columns = ["session_id", "world_id", "difficulty", "event_type", "timestamp",
               "time_in_session_s", "value1", "value2", "value3"]
    df = pd.DataFrame(gameforge_events)[columns] if gameforge_events else pd.DataFrame(columns=columns)
    dataset_id = str(uuid.uuid4())
    datasets[dataset_id] = {
        "meta": {
            "name": "GameForge Player Data",
            "rows": len(df),
            "columns": len(df.columns),
            "source": "gameforge",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
        "df": df,
        "schema": None,
        "quality": None,
        "findings": [],
        "model": {},
        "stress_test": {},
        "report": {},
    }
    return {
        "dataset_id": dataset_id,
        "name": "GameForge Player Data",
        "rows": len(df),
        "columns": len(df.columns),
        "preview": _df_preview(df),
    }
