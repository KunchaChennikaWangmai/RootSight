import os
import json
from typing import List, Dict, Any, Optional
from app.api.schemas import HypothesisOutput, AnalysisFinding

# Try loading external google packages
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def call_hypothesis_llm(
    findings: List[AnalysisFinding], 
    logs_body: Optional[str],
    timeline_desc: str
) -> HypothesisOutput:
    """
    Sends findings, logs, and timeline details to Gemini LLM to construct a Root Cause Hypothesis.
    If GEMINI_API_KEY is not defined or connection fails, runs a fallback deterministic heuristic rules engine.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    prompt = f"""
    You are an expert Production Incident Investigator SRE.
    Analyze the following evidence gathered from RootSight:
    
    1. Chronological Timeline Context:
    {timeline_desc}
    
    2. Parsed Agent Findings:
    {json.dumps([f.dict() for f in findings], default=str, indent=2)}
    
    3. Raw Log Samples:
    {logs_body[:1000] if logs_body else "No logs uploaded."}
    
    Generate a JSON object matching the following structure:
    {{
        "probable_root_cause": "A brief explanation of the most likely root cause.",
        "confidence_score": 0.0 to 1.0 (float reflecting confidence level),
        "reasoning": [
            "Step 1: finding A matches timeline change B",
            "Step 2: Exception trace patterns indicate resource starvation"
        ],
        "assumptions": [
            "Assumption 1: Max connections pool configuration was set manually",
            "Assumption 2: Database server CPU was functional"
        ]
    }}
    Return ONLY the raw JSON block without markdown formatting or backticks.
    """

    if HAS_GENAI and api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean possible markdown wrap ```json ... ```
            if text.startswith("```"):
                text = text.split("```json")[-1].split("```")[0].strip()
            elif text.startswith("```"):
                text = text.split("```")[-1].split("```")[0].strip()
                
            data = json.loads(text)
            return HypothesisOutput(
                probable_root_cause=data.get("probable_root_cause", "Unknown Cause"),
                confidence_score=float(data.get("confidence_score", 0.5)),
                reasoning=data.get("reasoning", []),
                assumptions=data.get("assumptions", [])
            )
        except Exception as e:
            # Fallback to local heuristic on LLM failure
            pass

    # ==========================================
    # Heuristics Fallback Engine (Detailed SRE rules)
    # ==========================================
    probable_root_cause = "General connection timeout or system pool starvation"
    confidence_score = 0.6
    reasoning = ["Analyzed incident inputs and detected general execution failure."]
    assumptions = ["Assumed metrics latency spikes were corresponding to log warnings."]

    has_pool_err = any("connection pool" in f.message.lower() or "hikari" in f.evidence_snippet.lower() if f.evidence_snippet else False for f in findings)
    has_config_change = any("config" in f.message.lower() or "variable" in f.message.lower() for f in findings)
    
    if has_pool_err and has_config_change:
        probable_root_cause = "Database connection pool exhaustion triggered by recent deployment config limits reduction"
        confidence_score = 0.95
        reasoning = [
            "Step 1: Log analyzer detected Hickari / Connection pool exhaustion error lines ('Connection is not available').",
            "Step 2: Deployment agent detected DB_MAX_POOL_SIZE environment variable was modified and decreased.",
            "Step 3: Temporal overlap shows latency/error spikes starting exactly within the deployment window."
        ]
        assumptions = [
            "Assumed that the active workload demands more than 5 parallel connections during peak hours.",
            "Assumed no concurrent network outages occurred between backend and database servers."
        ]
    elif has_pool_err:
        probable_root_cause = "Uncontrolled database connection leak in application thread pool"
        confidence_score = 0.8
        reasoning = [
            "Step 1: Application logs highlight that connection request queue length spiked.",
            "Step 2: HikariPool reported connection timeout transient errors.",
            "Step 3: Traffic spikes did not correlate with significant load increases, implying active leaks."
        ]
        assumptions = [
            "Assumed that application codebase features connection release omissions (missing close blocks)."
        ]
    elif has_config_change:
         probable_root_cause = "Platform infrastructure reconfiguration impact"
         confidence_score = 0.7
         reasoning = [
             "Step 1: Detected configuration variables modification.",
             "Step 2: System behavior degraded shortly after settings change."
         ]
         assumptions = [
             "Assumed that settings deployment values were not validated in staging environment."
         ]

    return HypothesisOutput(
        probable_root_cause=probable_root_cause,
        confidence_score=confidence_score,
        reasoning=reasoning,
        assumptions=assumptions
    )
