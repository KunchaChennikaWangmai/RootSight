from typing import Dict, Any, List

def compute_config_diff(deployment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Analyzes configuration changes or flags provided inside deployment metadata, 
    matching them against expected Baselines or detecting risky changes.
    """
    changes = []
    
    # Check if there is an active comparison configuration provided (e.g. baseline or previous config)
    current_vars = deployment_data.get("config_vars", {})
    previous_vars = deployment_data.get("previous_config_vars", None)
    
    if previous_vars is None:
        # If no baseline is provided, flag suspicious environment changes or empty settings
        for key, val in current_vars.items():
            key_upper = key.upper()
            if any(term in key_upper for term in ["TIMEOUT", "POOL", "SIZE", "LIMIT", "MAX", "MIN"]):
                # Flag resource-related configs for informational purposes
                changes.append({
                    "type": "METADATA",
                    "key": key,
                    "previous": "Unknown",
                    "current": str(val),
                    "description": f"Resource limit config variable detected: {key} = {val}"
                })
        return changes

    # Full comparison if previous configs exist
    all_keys = set(current_vars.keys()).union(set(previous_vars.keys()))
    
    for key in all_keys:
        prev_val = previous_vars.get(key)
        curr_val = current_vars.get(key)
        
        if prev_val is None:
            changes.append({
                "type": "ADDED",
                "key": key,
                "previous": "None",
                "current": str(curr_val),
                "description": f"Configuration variable added: {key} = {curr_val}"
            })
        elif curr_val is None:
            changes.append({
                "type": "REMOVED",
                "key": key,
                "previous": str(prev_val),
                "current": "None",
                "description": f"Configuration variable deleted: {key}"
            })
        elif prev_val != curr_val:
            changes.append({
                "type": "MODIFIED",
                "key": key,
                "previous": str(prev_val),
                "current": str(curr_val),
                "description": f"Configuration variable changed: {key} went from '{prev_val}' to '{curr_val}'"
            })
            
    return changes
