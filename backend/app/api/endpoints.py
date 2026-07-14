import uuid
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.api.schemas import IncidentPayload, InvestigationReportResponse
from app.core.orchestrator import run_incident_investigation

router = APIRouter(prefix="/investigations", tags=["Investigations"])

# In-memory storage for demonstrations
incident_db = {}

@router.post("/analyze", response_model=InvestigationReportResponse)
async def analyze_incident(payload: IncidentPayload):
    """
    Accepts raw data files (logs, metrics, configs, stack traces), compiles the incident state,
    and runs the LangGraph AI multi-agent workflow to analyze the incident and generate a report.
    """
    try:
        # Generate an investigation ID
        incident_id = str(uuid.uuid4())
        
        # Run the Multi-Agent orchestrator
        report = run_incident_investigation(incident_id, payload)
        
        # Save to mock database
        incident_db[incident_id] = report
        
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process investigation: {str(e)}")

@router.get("/{incident_id}", response_model=InvestigationReportResponse)
async def get_incident(incident_id: str):
    """
    Fetches the detailed investigation findings, timeline, and report for a specific incident.
    """
    if incident_id not in incident_db:
         # Return a simulated historical incident if not found, to help frontend developers
         if incident_id == "sample-incident-uuid":
              raise HTTPException(status_code=404, detail="Sample requested, but db is empty. Perform an analysis first.")
         raise HTTPException(status_code=404, detail="Incident investigation not found")
    return incident_db[incident_id]

@router.get("", response_model=List[dict])
async def list_incidents():
    """
    Retrieves high-level metadata for all analyzed incident investigations.
    """
    return [
        {
            "incident_id": inc_id,
            "title": record.title if hasattr(record, "title") else "Production Outage Investigation",
            "status": record.status,
            "findings_count": len(record.findings),
            "recommendations_count": len(record.recommendations)
        }
        for inc_id, record in incident_db.items()
    ]
