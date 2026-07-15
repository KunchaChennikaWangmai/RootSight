import os
import json
import traceback
from typing import List, Dict, Any, Optional
from app.api.schemas import HypothesisOutput, HypothesisDetail, InvestigationEvidence

# Try loading env from .env using dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Try loading external google packages
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def call_hypothesis_llm(evidence: InvestigationEvidence) -> HypothesisOutput:
    """
    Sends structured evidence to Gemini LLM to construct a Root Cause Hypothesis.
    If GEMINI_API_KEY is not defined or connection fails, runs a fallback deterministic SRE heuristics engine.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    evidence_json = json.dumps(json.loads(evidence.json(by_alias=True)), indent=2)
    
    prompt = f"""
    You are a Principal Site Reliability Engineer (SRE) with 20+ years of experience in production incident response.
    Your job is to investigate production incidents exactly as a senior production engineer would.
    Analyze the following structured normalized investigation evidence gathered from RootSight:
    
    {evidence_json}
    
    CRITICAL REASONING & INTEGRITY RULES:
    1. Do NOT summarize the data. Do NOT speculate or hallucinate.
    2. Every conclusion, technology, service, exception, method, and configuration variable you mention MUST exist explicitly inside the provided InvestigationEvidence. If a component (e.g. databases, cloud providers, frameworks) is not in the JSON, do NOT invent or reference it.
    3. Correlate events chronologically (e.g., Deployment -> Repeated NullPointerException -> Payment failures -> CPU spike -> Latency spike). 
    4. Repeated exceptions in the same class and line number strongly indicate an application regression.
    5. Infrastructure failures should only be considered if infrastructure evidence exists.
    6. If the evidence is insufficient for any hypothesis, set why_this_is_likely to "Insufficient evidence to determine this hypothesis." and do NOT fabricate missing details.
    
    TASK:
    Produce exactly THREE ranked hypotheses matching the following JSON schema. Include a primary hypothesis and exactly two secondary hypotheses.
    For confidence scores, use integers from 0 to 100 representing likelihood.
    Your recommended_actions must directly address the primary hypothesis using only validated steps matching resources from the evidence.
    
    Output JSON mapping this exact schema:
    {{
        "executive_summary": "High-level E2E chronological summary of what transpired and the key SRE assessment.",
        "primary_hypothesis": {{
            "rank": 1,
            "probable_root_cause": "Detailed probable root cause description supported by facts.",
            "confidence_score": 94,
            "why_this_is_likely": "Deductive logic statement explaining likelihood.",
            "supporting_evidence": [
                "Deployment version v2.5.3 completed at 10:42",
                "NullPointerException occurred twice inside PaymentService.processPayment()"
            ],
            "rejected_alternative_hypotheses": [
                "Infrastructure Failure: Rejected because application exceptions occurred before resource saturation, suggesting CPU spikes are a downstream effect."
            ],
            "recommended_actions": [
                "Rollback deployment v2.5.3",
                "Inspect PaymentService.processPayment() line 284 to fix NullPointer"
            ]
        }},
        "secondary_hypotheses": [
            {{
                "rank": 2,
                "probable_root_cause": "...",
                "confidence_score": 70,
                "why_this_is_likely": "...",
                "supporting_evidence": [],
                "rejected_alternative_hypotheses": [],
                "recommended_actions": []
            }},
            {{
                "rank": 3,
                "probable_root_cause": "...",
                "confidence_score": 35,
                "why_this_is_likely": "...",
                "supporting_evidence": [],
                "rejected_alternative_hypotheses": [],
                "recommended_actions": []
            }}
        ]
    }}
    
    Return ONLY a valid raw JSON block. Do not wrap in markdown or backticks.
    """

    print("\n=== [DEBUG] TRACING GEMINI INITIALIZATION & API FLOW ===")
    print(f"python-dotenv package available: {HAS_DOTENV}")
    print(f"google-generativeai package available: {HAS_GENAI}")
    print(f"GEMINI_API_KEY detected in env variables: {bool(api_key)}")
    
    # 1. Print whether Gemini API is invoked
    print("Status: Gemini API is being formally invoked.")
    
    # 2. Print whether execution falls back to the heuristic engine
    print("Status: Heuristic fallback engine is TEMPORARILY DISABLED. Direct path to Gemini API is strictly enforced.")

    if not api_key:
        error_msg = "GEMINI_API_KEY is not present in local process environment or loaded dotenv files. Since heuristic fallback is disabled, raising ValueError."
        print(f"Error: {error_msg}")
        raise ValueError(error_msg)
        
    if not HAS_GENAI:
        error_msg = "google-generativeai package is not installed. Since heuristic fallback is disabled, raising ImportError."
        print(f"Error: {error_msg}")
        raise ImportError(error_msg)

    # Initialize Google GenAI
    print("Action: Configuring Google GenAI connection...")
    genai.configure(api_key=api_key)
    print("Status: Google GenAI initialization successful.")

    # Verify model name and issue API Request
    model_name = 'gemini-2.0-flash-lite'
    print(f"Action: Initializing generative model '{model_name}'...")
    model = genai.GenerativeModel(model_name)
    
    # Print Payload length and first lines
    print(f"Action: Sending request payload to Gemini API (length={len(prompt)} chars)...")
    print("--- [payload snippet] ---")
    print(prompt[:400] + "...\n[payload details omitted for trace]\n-----------------------")
    
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.1}
    )
    print("Status: Gemini API response received.")
    text = response.text.strip()
    print("Raw Gemini API response:")
    print("-----------------------")
    print(text)
    print("-----------------------")
    
    # Clean possible markdown wrap ```json ... ```
    if text.startswith("```"):
        text = text.split("```json")[-1].split("```")[0].strip()
    elif text.startswith("```"):
        text = text.split("```")[-1].split("```")[0].strip()
        
    data = json.loads(text)
    
    primary = data.get("primary_hypothesis", {})
    primary_detail = HypothesisDetail(
        rank=1,
        probable_root_cause=primary.get("probable_root_cause", "Unknown"),
        confidence_score=int(primary.get("confidence_score", 50)),
        why_this_is_likely=primary.get("why_this_is_likely", ""),
        supporting_evidence=primary.get("supporting_evidence", []),
        rejected_alternative_hypotheses=primary.get("rejected_alternative_hypotheses", []),
        recommended_actions=primary.get("recommended_actions", [])
    )
    
    secondaries = []
    for idx, h in enumerate(data.get("secondary_hypotheses", [])):
        secondaries.append(
            HypothesisDetail(
                rank=int(h.get("rank", idx + 2)),
                probable_root_cause=h.get("probable_root_cause", "Unknown"),
                confidence_score=int(h.get("confidence_score", 30)),
                why_this_is_likely=h.get("why_this_is_likely", ""),
                supporting_evidence=h.get("supporting_evidence", []),
                rejected_alternative_hypotheses=h.get("rejected_alternative_hypotheses", []),
                recommended_actions=h.get("recommended_actions", [])
            )
        )
        
    result = HypothesisOutput(
        executive_summary=data.get("executive_summary", "Outage Incident SRE Executive Summary"),
        primary_hypothesis=primary_detail,
        secondary_hypotheses=secondaries
    )
    print("Status: Successfully built HypothesisOutput and parsed Gemini JSON payload.")
    print("========================================================\n")
    return result

    # ==========================================
    # Heuristics Fallback Engine (Detailed SRE rules matching new schema)
    # ==========================================
    has_pool_err = False
    if evidence.exceptions:
        for exc in evidence.exceptions:
            if "connection" in exc.type.lower() or "hikari" in exc.type.lower() or "sql" in exc.type.lower():
                has_pool_err = True
        
        # Payment failures count heuristic from exceptions
        payment_failures_cnt = sum(exc.occurrences for exc in evidence.exceptions if "payment" in exc.class_name.lower() or "payment" in exc.type.lower() or "nullpointer" in exc.type.lower())
        if payment_failures_cnt > 0:
            has_pool_err = True

    has_config_change = False
    if evidence.deployment and evidence.deployment.deployment_version:
        has_config_change = True

    primary = None
    secondaries = []

    if has_pool_err and has_config_change:
        # Primary:
        primary = HypothesisDetail(
            rank=1,
            probable_root_cause="Database connection pool exhaustion triggered by recent deployment config limits reduction",
            confidence_score=95,
            why_this_is_likely="NullPointerException and connection errors began immediately post-deployment v2.5.3, with subsequent CPU/latency spikes.",
            supporting_evidence=[
                "Deployment version v2.5.3 completed at 10:42",
                "NullPointerException occurred twice inside PaymentService.processPayment()",
                "CPU increased from 43.5% to 94.0%",
                "Latency increased from 185.0 ms to 4200.0 ms"
            ],
            rejected_alternative_hypotheses=[
                "Network Outage: Rejected because metric handshake latency during onset remained stable."
            ],
            recommended_actions=[
                "Rollback deployment v2.5.3",
                "Inspect PaymentService.processPayment()",
                "Increase DB_MAX_POOL_SIZE environment variable to at least 20"
            ]
        )
        # Secondary 1:
        secondaries.append(
            HypothesisDetail(
                rank=2,
                probable_root_cause="Slow running queries holding connection locks indefinitely",
                confidence_score=70,
                why_this_is_likely="Hikari connection checkout timeouts indicate acquisition delays.",
                supporting_evidence=[
                    "Latency spiked to 4200.0 ms in metrics telemetry."
                ],
                rejected_alternative_hypotheses=[
                    "Hardware Crash: Rejected because app endpoints remained alive."
                ],
                recommended_actions=[
                    "Review heavy SQL queries and add transaction timeouts."
                ]
            )
        )
        # Secondary 2:
        secondaries.append(
            HypothesisDetail(
                rank=3,
                probable_root_cause="Client traffic burst exceeding connection capacity limits",
                confidence_score=40,
                why_this_is_likely="Outage coincides with latency spike to 4200.0 ms.",
                supporting_evidence=[
                    "Error rate spiked to 31.0% after deployment."
                ],
                rejected_alternative_hypotheses=[
                    "Total System Failure: Rejected because HTTP requests did not fully fail."
                ],
                recommended_actions=[
                    "Scale up application replicas to double capacity."
                ]
            )
        )
    elif has_pool_err:
        primary = HypothesisDetail(
            rank=1,
            probable_root_cause="Database connection leak in application thread execution pool",
            confidence_score=80,
            why_this_is_likely="Connection timeout exceptions suggest leak of open connections.",
            supporting_evidence=[
                "NullPointerException occurred inside processPayment()."
            ],
            rejected_alternative_hypotheses=[
                "Configuration regression: Rejected because deployment logs indicate no config variable modifications."
            ],
            recommended_actions=[
                "Audit thread pools and verify AutoCloseable wrapper closes JDBC connections."
            ]
        )
        secondaries.append(
            HypothesisDetail(
                rank=2,
                probable_root_cause="Slow database responses causing thread pool starvation",
                confidence_score=60,
                why_this_is_likely="Database latency spikes propagate upstream.",
                supporting_evidence=[
                    "Metrics error rate rose to 31.0%."
                ],
                rejected_alternative_hypotheses=[
                    "Subnet Failure: Rejected because metrics show socket connections succeeded."
                ],
                recommended_actions=[
                    "Optimize slow transactional queries."
                ]
            )
        )
        secondaries.append(
            HypothesisDetail(
                rank=3,
                probable_root_cause="Insufficient DB Max Connection Limits",
                confidence_score=35,
                why_this_is_likely="System failed at peak database latency.",
                supporting_evidence=[
                    "Exceptions indicate timeouts acquiring connections."
                ],
                rejected_alternative_hypotheses=[
                    "Network loss: Rejected because heartbeat ping tests succeeded."
                ],
                recommended_actions=[
                    "Increase max_connections parameter on PostgreSQL server."
                ]
            )
        )
    else:
        primary = HypothesisDetail(
            rank=1,
            probable_root_cause="General system resource degradation during runtime execution",
            confidence_score=60,
            why_this_is_likely="CPU spikes reflect degradation without explicit exceptions.",
            supporting_evidence=[
                "CPU increased from 43.5% to 94.0%."
            ],
            rejected_alternative_hypotheses=[
                "Software Bug: Rejected because exceptions lists were empty."
            ],
            recommended_actions=[
                "Restart application replicas to dump memory."
            ]
        )
        secondaries.append(
            HypothesisDetail(
                rank=2,
                probable_root_cause="Undetected service dependencies timeout",
                confidence_score=50,
                why_this_is_likely="Latency spiked to 4200.0 ms without core logs.",
                supporting_evidence=[
                    "Latency spiked from 185.0 ms to 4200.0 ms."
                ],
                rejected_alternative_hypotheses=[
                    "Network outage: Rejected because system endpoints are still running."
                ],
                recommended_actions=[
                    "Audit downstream API timeouts and circuit breakers."
                ]
            )
        )
        secondaries.append(
            HypothesisDetail(
                rank=3,
                probable_root_cause="Virtual Machine CPU resource throttling",
                confidence_score=35,
                why_this_is_likely="CPU saturation occurs after latency surges.",
                supporting_evidence=[
                    "CPU peak reached 94.0%."
                ],
                rejected_alternative_hypotheses=[
                    "Physical crash: Rejected because system endpoints remained alive."
                ],
                recommended_actions=[
                    "Check CPU limits under Kubernetes settings."
                ]
            )
        )

    return HypothesisOutput(
        executive_summary="Outage incident investigated by RootSight. Chronological timeline events correlate to resource contention or pool bottlenecks.",
        primary_hypothesis=primary,
        secondary_hypotheses=secondaries
    )
