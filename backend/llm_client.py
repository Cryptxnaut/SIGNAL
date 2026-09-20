import json
import httpx
from typing import AsyncGenerator

from domain_detector import get_domain_system_prompt, Domain

OLLAMA_BASE = "http://localhost:11434"
MODEL = "qwen2.5:72b"
TIMEOUT = 60.0


class LLMOfflineError(Exception):
    pass


async def generate(
    prompt: str, system: str = "", stream: bool = False
) -> "str | AsyncGenerator":
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": stream,
    }
    if system:
        payload["system"] = system

    try:
        if not stream:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE}/api/generate", json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        else:
            # Return an async generator
            return _stream_generate(payload)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise LLMOfflineError(f"Ollama not reachable: {e}") from e


async def _stream_generate(payload: dict) -> AsyncGenerator[str, None]:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{OLLAMA_BASE}/api/generate", json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise LLMOfflineError(f"Ollama stream failed: {e}") from e


async def generate_hypotheses(schema: dict, intent: str, domain: str = "general") -> list:
    system = get_domain_system_prompt(domain) + (
        " Given a dataset schema and a user's analytical intent, return a JSON analysis plan. "
        "Return ONLY valid JSON, no preamble, no markdown."
    )
    user = (
        f"Schema: {json.dumps(schema)}\n\n"
        f"Intent: {intent}\n\n"
        "Return a JSON object with key 'hypotheses': an array of up to 8 objects, each with keys: "
        "'name' (short title), "
        "'type' ('correlation'|'mutual_info'|'anomaly'|'trend'|'leading_indicator'|'regime_change'|'clustering'), "
        "'target_column' (column to analyse), "
        "'feature_columns' (array of columns to use), "
        "'description' (one sentence). "
        "Include at least one 'mutual_info' hypothesis to detect non-linear relationships, "
        "and at least one 'clustering' hypothesis to find natural groupings in the data."
    )

    try:
        response = await generate(user, system=system, stream=False)
        # Strip markdown fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        parsed = json.loads(text)
        hypotheses = parsed.get("hypotheses", [])
        if not isinstance(hypotheses, list):
            raise ValueError("hypotheses is not a list")
        return hypotheses
    except Exception:
        return _fallback_hypotheses(schema)


def _fallback_hypotheses(schema: dict) -> list:
    columns_meta = schema.get("columns", {})
    numeric_cols = [
        col for col, info in columns_meta.items()
        if info.get("dtype") == "numeric"
    ][:6]

    hypotheses = []
    if len(numeric_cols) >= 2:
        hypotheses.append({
            "name": f"Correlation: {numeric_cols[0]} vs {numeric_cols[1]}",
            "type": "correlation",
            "target_column": numeric_cols[0],
            "feature_columns": numeric_cols[1:3],
            "description": f"Explore linear and rank correlations between {numeric_cols[0]} and {numeric_cols[1]}.",
        })
    if len(numeric_cols) >= 2:
        hypotheses.append({
            "name": f"Non-linear signals in {numeric_cols[0]}",
            "type": "mutual_info",
            "target_column": numeric_cols[0],
            "feature_columns": numeric_cols[1:],
            "description": f"Detect non-linear relationships driving {numeric_cols[0]} using mutual information.",
        })
    if len(numeric_cols) >= 1:
        hypotheses.append({
            "name": f"Anomaly detection on {numeric_cols[0]}",
            "type": "anomaly",
            "target_column": numeric_cols[0],
            "feature_columns": numeric_cols[:3],
            "description": f"Detect statistical anomalies in {numeric_cols[0]}.",
        })
    if len(numeric_cols) >= 1:
        hypotheses.append({
            "name": f"Trend analysis of {numeric_cols[0]}",
            "type": "trend",
            "target_column": numeric_cols[0],
            "feature_columns": [],
            "description": f"Decompose and analyse the trend in {numeric_cols[0]}.",
        })
    if len(numeric_cols) >= 2:
        hypotheses.append({
            "name": "Natural groupings in data",
            "type": "clustering",
            "target_column": numeric_cols[0],
            "feature_columns": numeric_cols[:5],
            "description": "Identify natural clusters and groupings across numeric features.",
        })
    return hypotheses


async def explain_finding(finding: dict, intent: str, domain: str = "general") -> str:
    system = get_domain_system_prompt(domain)
    safe_finding = {k: v for k, v in finding.items() if not k.startswith("_") and k not in ["correlations", "granger_results", "mi_results", "anomalous_rows", "cluster_profiles"]}
    top_corr = finding.get("top_correlation", {})
    effect_context = ""
    if top_corr:
        r = top_corr.get("r", 0)
        p = top_corr.get("p", 1)
        d = top_corr.get("cohens_d", 0)
        effect_context = f" The top correlation has r={r}, p={p:.4f}, Cohen's d={d}."
    prompt = (
        f"Explain this finding in 2 sentences for a non-technical executive.{effect_context} "
        f"Finding: {json.dumps(safe_finding)}. "
        f"Dataset intent: {intent}. "
        "Return only the explanation, no preamble."
    )
    try:
        result = await generate(prompt, system=system, stream=False)
        return result.strip()
    except LLMOfflineError:
        return finding.get("name", "Unnamed finding")


async def explain_findings_batch(findings: list, intent: str, domain: str = "general") -> dict:
    """Explain all findings in a single LLM call — much faster than one-by-one."""
    if not findings:
        return {}
    system = get_domain_system_prompt(domain)
    findings_text = "\n\n".join([
        f"Finding {i+1}: {json.dumps({k: v for k, v in f.items() if not k.startswith('_') and k not in ['correlations', 'granger_results', 'mi_results', 'anomalous_rows', 'cluster_profiles']})}"
        for i, f in enumerate(findings[:5])
    ])
    prompt = f"""Dataset intent: {intent}

{findings_text}

For each finding above, write exactly ONE sentence of plain-English executive explanation. Number them 1-{min(5, len(findings))}. Format as:
1. [explanation]
2. [explanation]
...

No preamble. No markdown. Each explanation must mention the key metric."""
    try:
        response = await generate(prompt, system=system)
        lines = [l.strip() for l in response.strip().split("\n") if l.strip()]
        result = {}
        for i, finding in enumerate(findings[:5]):
            # Find the numbered line
            prefix = f"{i+1}."
            match = next((l[len(prefix):].strip() for l in lines if l.startswith(prefix)), None)
            if match:
                result[finding.get("name", str(i))] = match
        return result
    except LLMOfflineError:
        return {}


async def executive_summary(report_data: dict) -> str:
    prompt = (
        f"You are a senior data analyst writing for C-suite executives. "
        f"Write a 3-4 sentence executive summary for this analysis report. "
        f"Report data: {json.dumps(report_data)}. "
        "Be concise, highlight the most important findings, and recommend next steps."
    )
    try:
        result = await generate(prompt, stream=False)
        return result.strip()
    except LLMOfflineError:
        findings = report_data.get("findings", [])
        n = len(findings)
        return (
            f"The analysis identified {n} significant findings in the dataset. "
            "Key correlations and anomalies have been detected. "
            "Review the findings tab for detailed statistical evidence. "
            "Model training results are available in the Model tab."
        )


async def stream_consultant(
    message: str, history: list, context: dict
) -> AsyncGenerator[str, None]:
    schema = context.get("schema", {})
    findings = context.get("findings", [])
    model_metrics = context.get("model", {})

    findings_summary = []
    for f in findings[:5]:
        findings_summary.append({
            "name": f.get("name"),
            "type": f.get("type"),
            "significance_score": f.get("significance_score"),
        })

    system = (
        "You are SIGNAL, an expert data analyst AI assistant. You have full access to the dataset context below. "
        "Answer the user's questions concisely and accurately. Use the data to support your answers.\n\n"
        f"Dataset Schema: {json.dumps(schema)}\n\n"
        f"Top Findings: {json.dumps(findings_summary)}\n\n"
        f"Model Metrics: {json.dumps(model_metrics)}"
    )

    # Build conversation history prompt
    history_text = ""
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        history_text += f"{role.capitalize()}: {content}\n"

    full_prompt = history_text + f"User: {message}\nAssistant:"

    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "system": system,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", f"{OLLAMA_BASE}/api/generate", json=payload
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        yield "I'm sorry, the LLM service is currently offline. Please ensure Ollama is running."
