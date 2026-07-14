import re
from typing import List, Dict, Any

def parse_stack_trace(stack_content: str) -> List[Dict[str, Any]]:
    """
    Parses traceback logs (Python, Java, Node.js style) into structured frames.
    """
    frames = []
    lines = stack_content.splitlines()
    
    # Python-style: File "filename.py", line 12, in function_name
    python_pattern = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<function>\w+)')
    # Java-style: at package.class.method(FileName.java:12)
    java_pattern = re.compile(r'at (?P<package_method>[\w\.\$]+\.\w+)\((?P<file_line>[\w\.]+:\d+|Native Method|Unknown Source)\)')
    # Node-style: at method (path/to/file.js:12:34) or at path/to/file.js:12:34
    node_pattern = re.compile(r'at (?P<method>[\w\.]+)?\s*\(?(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)\)?')

    exception_type = "UnknownException"
    exception_message = ""
    
    # Simple search for Exception line (often the first line in Java/Node, or the last line in Python)
    for line in lines:
        line_strip = line.strip()
        # Common exception declarations, e.g., ValueError: index out of range or java.lang.NullPointerException
        if ":" in line_strip and not line_strip.startswith("at ") and not line_strip.startswith("File "):
            parts = line_strip.split(":", 1)
            parts_type = parts[0].strip()
            # If the part looks like a class name or standard python error name
            if len(parts_type) > 3 and ("Exception" in parts_type or "Error" in parts_type or parts_type[0].isupper()):
                exception_type = parts_type
                exception_message = parts[1].strip()
                break

    for line in lines:
        line_strip = line.strip()
        
        # Check Python
        py_match = python_pattern.search(line_strip)
        if py_match:
            frames.append({
                "language": "python",
                "file": py_match.group("file"),
                "line": int(py_match.group("line")),
                "function": py_match.group("function"),
                "raw": line_strip
            })
            continue
            
        # Check Java
        java_match = java_pattern.search(line_strip)
        if java_match:
            pkg_method = java_match.group("package_method")
            file_line = java_match.group("file_line")
            file_name = "Unknown"
            line_no = 0
            if ":" in file_line:
                file_name, line_no = file_line.split(":", 1)
                line_no = int(line_no) if line_no.isdigit() else 0
            
            frames.append({
                "language": "java",
                "file": file_name,
                "line": line_no,
                "function": pkg_method.split(".")[-1],
                "package": ".".join(pkg_method.split(".")[:-1]),
                "raw": line_strip
            })
            continue

        # Check Node.js
        node_match = node_pattern.search(line_strip)
        if node_match:
            frames.append({
                "language": "node",
                "file": node_match.group("file"),
                "line": int(node_match.group("line")),
                "function": node_match.group("method") or "anonymous",
                "raw": line_strip
            })
            continue
            
    return {
        "exception_type": exception_type,
        "exception_message": exception_message,
        "frames": frames
    }
