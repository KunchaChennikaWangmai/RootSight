import re
from typing import List, Dict, Any

def parse_logs(log_content: str) -> List[Dict[str, Any]]:
    """
    Deterministically parses logs to find errors, warnings, and group similar messages.
    """
    parsed_entries = []
    lines = log_content.splitlines()
    
    # Regex to capture timestamp, level, and message (Common patterns)
    log_pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?'
        r'\s*\[?(?P<level>INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|DEBUG)\]?'
        r'\s*(?P<message>.*)', 
        re.IGNORECASE
    )

    for line_num, line in enumerate(lines, 1):
        match = log_pattern.search(line)
        if match:
            group = match.groupdict()
            level = (group.get("level") or "INFO").upper()
            message = group.get("message") or line
            timestamp = group.get("timestamp") or ""
            
            # Identify abnormal levels
            if level in ["ERROR", "FATAL", "CRITICAL", "WARN", "WARNING"]:
                parsed_entries.append({
                    "line_number": line_num,
                    "timestamp": timestamp,
                    "level": level,
                    "message": message.strip()
                })
        else:
            # Fallback for multiline content or unformatted chunks
            if any(err_word in line.upper() for err_word in ["ERROR", "EXCEPTION", "FAIL", "CRITICAL"]):
                parsed_entries.append({
                    "line_number": line_num,
                    "timestamp": "",
                    "level": "ERROR",
                    "message": line.strip()
                })
                
    return parsed_entries

def cluster_log_errors(parsed_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups error lines by template. (Removes digits, UUIDs, IPs to discover core error patterns)
    """
    clusters = {}
    for entry in parsed_entries:
        # Create a template by stripping dynamic variables
        msg = entry["message"]
        template = re.sub(r'\d+', 'ID', msg) # Replace numbers
        template = re.sub(r'0x[0-9a-fA-F]+', 'HEX', template) # Replace hex
        template = re.sub(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}', 'UUID', template) # UUIDs
        template = template.strip()

        if template not in clusters:
            clusters[template] = {
                "template": template,
                "count": 0,
                "first_seen_line": entry["line_number"],
                "level": entry["level"],
                "examples": []
            }
        
        clusters[template]["count"] += 1
        if len(clusters[template]["examples"]) < 3:
            clusters[template]["examples"].append(entry["message"])
            
    return list(clusters.values())
