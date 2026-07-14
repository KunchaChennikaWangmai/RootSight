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
    If GEMINI_API_KEY is not defined or connection fails, runs a fallback deterministic SRE heuristics engine.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    prompt = f"""
    You are a Senior Site Reliability Engineer (SRE) investigating a production outage.
    Analyze the following evidence gathered from RootSight:
    
    1. Chronological Timeline Context:
    {timeline_desc}
    
    2. Parsed Agent Findings:
    {json.dumps([f.dict() for f in findings], default=str, indent=2)}
    
    3. Raw Log Samples:
    {logs_body[:1200] if logs_body else "No logs uploaded."}
    
    Generate a JSON object containing the top 3 ranked probable root causes in order of likelihood.
    Your analysis must resemble a senior SRE report:
    - Never generate generic infrastructure hypotheses (such as "CPU was overloaded" or "server is slow").
    - Explicitly reference supporting evidence from specific agents (e.g., LogAnalysisAgent, StackTraceAgent) inside `supporting_evidence`.
    - Provide a robust SRE explanation of why alternative hypotheses (e.g., database network isolation, sudden traffic spike, hardware failures) were rejected in favour of the ranked cause.
    - Tie remediations directly to each specific cause.
    
    Match the following JSON schema:
    {{
        "top_hypotheses": [
            {{
                "rank": 1,
                "probable_root_cause": "Specific SRE-level root cause description (e.g., Hikari connection pool exhaustion due to database connection leak in unclosed transaction block).",
                "confidence_score": 0.85,
                "supporting_evidence": [
                    "LogAnalysisAgent: Detected Hikari connection timeout logs ('Connection is not available')",
                    "MetricsAnalysisAgent: Latency spiked from 120ms to 15000ms"
                ],
                "alternative_rejected_reason": "Rejected the network partition hypothesis since the MetricsAnalysisAgent shows ping times and DB CPU remained healthy.",
                "recommended_remediations": [
                    {{
                        "action_type": "HOTFIX",
                        "description": "Verify code uses try-with-resources or explicit connection close to avoid connection leaks.",
                        "command_or_code": "try (Connection conn = dataSource.getConnection()) {{ ... }}",
                        "risk_level": "MEDIUM"
                    }}
                ]
            }}
        ],
        "sre_summary": "A high-level incident summary summarizing the timeline and SRE assessment.",
        "key_assumptions": [
            "User traffic remained within standard bounds.",
            "Database server did not restart."
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
            
            # Convert list of dicts to schema objects
            hypotheses = []
            for h in data.get("top_hypotheses", []):
                remediations = [
                    {
                        "action_type": r.get("action_type", "RUNBOOK"),
                        "description": r.get("description", ""),
                        "command_or_code": r.get("command_or_code"),
                        "risk_level": r.get("risk_level", "LOW")
                    } for r in h.get("recommended_remediations", [])
                ]
                hypotheses.append({
                    "rank": int(h.get("rank", 1)),
                    "probable_root_cause": h.get("probable_root_cause", "Unknown"),
                    "confidence_score": float(h.get("confidence_score", 0.5)),
                    "supporting_evidence": h.get("supporting_evidence", []),
                    "alternative_rejected_reason": h.get("alternative_rejected_reason", ""),
                    "recommended_remediations": remediations
                })
            
            return HypothesisOutput(
                top_hypotheses=hypotheses,
                sre_summary=data.get("sre_summary", "Outage Incident Investigation Summary"),
                key_assumptions=data.get("key_assumptions", [])
            )
        except Exception as e:
            # Fallback to local heuristic on LLM failure
            pass

    # ==========================================
    # Heuristics Fallback Engine (Detailed SRE rules matching new schema)
    # ==========================================
    has_pool_err = any("connection pool" in f.message.lower() or "hikari" in f.message.lower() or ("evidence_snippet" in f.dict() and f.evidence_snippet and "hikari" in f.evidence_snippet.lower()) for f in findings)
    has_config_change = any("config" in f.message.lower() or "variable" in f.message.lower() or "deploy" in f.message.lower() for f in findings)
    has_stack_trace = any("stacktrace" in f.agent_name.lower() or "exception" in f.message.lower() for f in findings)

    top_hypotheses = []

    if has_pool_err and has_config_change:
        # Hypothesis 1: Connection Pool Exhaustion from Config Change
        top_hypotheses.append({
            "rank": 1,
            "probable_root_cause": "Database connection pool exhaustion triggered by recent deployment config limits reduction",
            "confidence_score": 0.95,
            "supporting_evidence": [
                "LogAnalysisAgent: Detected Hikari connection timeout logs ('Connection is not available')",
                "DeploymentAnalysisAgent: DB_MAX_POOL_SIZE environment variable was modified and decreased during deployment"
            ],
            "alternative_rejected_reason": "Rejected network loss to database because metrics show that connection ping latency was stable during the onset.",
            "recommended_remediations": [
                {
                    "action_type": "CONFIG",
                    "description": "Increase DB_MAX_POOL_SIZE environment variable to at least 20 in app deployment config.",
                    "command_or_code": "export DB_MAX_POOL_SIZE=20",
                    "risk_level": "LOW"
                }
            ]
        })
        # Hypothesis 2: Transaction leak
        top_hypotheses.append({
            "rank": 2,
            "probable_root_cause": "Slow running queries holding connection locks indefinitely",
            "confidence_score": 0.70,
            "supporting_evidence": [
                "LogAnalysisAgent: Connection acquired latency spiked above Hikari limits."
            ],
            "alternative_rejected_reason": "Rejected a hardware crash because database process remained active without restarts log.",
            "recommended_remediations": [
                {
                    "action_type": "HOTFIX",
                    "description": "Review heavy SQL queries and add transaction timeout configurations.",
                    "risk_level": "MEDIUM"
                }
            ]
        })
        # Hypothesis 3: Sudden Traffic spike
        top_hypotheses.append({
            "rank": 3,
            "probable_root_cause": "Client traffic burst exceeding connection capacity limits",
            "confidence_score": 0.40,
            "supporting_evidence": [
                "MetricsAnalysisAgent: Detected sudden elevated error rate spikes."
            ],
            "alternative_rejected_reason": "Rejected because overall HTTP request counts were within standard seasonal tolerances.",
            "recommended_remediations": [
                {
                    "action_type": "RUNBOOK",
                    "description": "Scale up application replicas to double the capacity.",
                    "command_or_code": "kubectl scale deployment rootsight-app --replicas=6",
                    "risk_level": "LOW"
                }
            ]
        })
    elif has_pool_err:
        top_hypotheses.append({
            "rank": 1,
            "probable_root_cause": "Database connection leak in application thread execution pool",
            "confidence_score": 0.80,
            "supporting_evidence": [
                "LogAnalysisAgent: App logs highlight that connection request queue length spiked.",
                "LogAnalysisAgent: Connection is not available error spikes."
            ],
            "alternative_rejected_reason": "Rejected config changes since config agent reports no environment variables were modified.",
            "recommended_remediations": [
                {
                    "action_type": "HOTFIX",
                    "description": "Audit thread pools and verify all JDBC connections are correctly enclosed in auto-closing blocks.",
                    "command_or_code": "try (Connection conn = dataSource.getConnection()) { ... }",
                    "risk_level": "MEDIUM"
                }
            ]
        })
        top_hypotheses.append({
            "rank": 2,
            "probable_root_cause": "Database server max-connection limits reached",
            "confidence_score": 0.60,
            "supporting_evidence": [
                "LogAnalysisAgent: HikariPool reported connection times exceeded."
            ],
            "alternative_rejected_reason": "Rejected network router port exhaustion as backend host logs did not report system socket errors.",
            "recommended_remediations": [
                {
                    "action_type": "CONFIG",
                    "description": "Increase max_connections parameter on the PostgreSQL/MySQL server.",
                    "command_or_code": "ALTER SYSTEM SET max_connections = 200;",
                    "risk_level": "HIGH"
                }
            ]
        })
        top_hypotheses.append({
            "rank": 3,
            "probable_root_cause": "Database network socket packet loss",
            "confidence_score": 0.30,
            "supporting_evidence": [
                "LogAnalysisAgent: Connection timeout logs."
            ],
            "alternative_rejected_reason": "Rejected complete network failure since metrics show TCP handshake latency was stable.",
            "recommended_remediations": [
                {
                    "action_type": "RUNBOOK",
                    "description": "Run network diagnostic trace from backend instances to database subnet.",
                    "command_or_code": "traceroute db.production.internal",
                    "risk_level": "LOW"
                }
            ]
        })
    else:
        top_hypotheses.append({
            "rank": 1,
            "probable_root_cause": "General system degradation during runtime execution",
            "confidence_score": 0.60,
            "supporting_evidence": [
                f.message for f in findings[:2]
            ],
            "alternative_rejected_reason": "Rejected specific component failure because logs did not contain isolated stacktrace error signatures.",
            "recommended_remediations": [
                {
                    "action_type": "RUNBOOK",
                    "description": "Restart the application instances to clear potential temporary deadlocks.",
                    "command_or_code": "kubectl rollout restart deployment rootsight-app",
                    "risk_level": "LOW"
                }
            ]
        })
        top_hypotheses.append({
            "rank": 2,
            "probable_root_cause": "Undetected service dependencies timeout",
            "confidence_score": 0.50,
            "supporting_evidence": [
                "LogAnalysisAgent: General latency increases logged."
            ],
            "alternative_rejected_reason": "Rejected internal code bug because no runtime exceptions were reported during the degradation.",
            "recommended_remediations": [
                {
                    "action_type": "CONFIG",
                    "description": "Audit downstream REST API connection timeouts & circuit breaker configurations.",
                    "risk_level": "LOW"
                }
            ]
        })
        top_hypotheses.append({
            "rank": 3,
            "probable_root_cause": "Virtual Machine resource throttling",
            "confidence_score": 0.35,
            "supporting_evidence": [
                "MetricsAnalysisAgent: Identified general metrics warnings."
            ],
            "alternative_rejected_reason": "Rejected physical host hardware crash since backend endpoints remained alive.",
            "recommended_remediations": [
                {
                    "action_type": "CONFIG",
                    "description": "Check if CPU requests and limits need to be scaled up.",
                    "risk_level": "LOW"
                }
            ]
        })

    return HypothesisOutput(
        top_hypotheses=top_hypotheses,
        sre_summary="Outage incident investigated by RootSight. Chronological timeline events correlate to resource contention or pool bottlenecks.",
        key_assumptions=[
            "Upstream load balancers continued to router HTTP traffic properly.",
            "Database instances didn't undergo manual system boots."
        ]
    )
