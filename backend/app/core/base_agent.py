import os
import json
import copy
from typing import Callable, Any, Dict, List
from app.api.schemas import AnalysisFinding

# Global registry to track tool executions per node session context
executed_tools_in_session: List[str] = []

class Tool:
    """
    A deterministic tool wrap representing a python function that can be executed.
    """
    def __init__(self, name: str, description: str, func: Callable[..., Any]):
        self.name = name
        self.description = description
        self.func = func

    def run(self, *args, **kwargs) -> Any:
        return self.func(*args, **kwargs)

class BaseAgent:
    """
    An agent wrapper that maintains a prompt scope and access to registered Tools.
    """
    def __init__(self, name: str, role: str, system_prompt: str, tools: List[Tool] = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools} if tools else {}

    def get_tool(self, tool_name: str) -> Tool:
        if tool_name not in self.tools:
            raise KeyError(f"Tool '{tool_name}' is not registered under Agent '{self.name}'")
        return self.tools[tool_name]

    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        tool = self.get_tool(tool_name)
        executed_tools_in_session.append(f"{self.name}.{tool_name}")
        return tool.run(*args, **kwargs)

def debug_node(node_name: str):
    """
    Decorator for dev-only debugging of LangGraph Node input/output state shifts and tool executions.
    """
    def decorator(func: Callable[..., Any]):
        def wrapper(state: Dict[str, Any], *args, **kwargs) -> Any:
            is_debug = os.getenv("DEBUG", "false").lower() == "true"
            is_dev = os.getenv("ENV", "development").lower() not in ["production", "prod"] and \
                     os.getenv("FASTAPI_ENV", "development").lower() not in ["production", "prod"]
            
            if not (is_debug and is_dev):
                return func(state, *args, **kwargs)

            # Clear session logs for this node execution slice
            executed_tools_in_session.clear()

            # Safely serialize state items
            def safe_serialize(obj: Any) -> Any:
                if hasattr(obj, "dict"):
                    return obj.dict()
                if hasattr(obj, "isoformat"):
                    return obj.isoformat()
                return str(obj)

            # Snapshot input state keys and values
            input_state = {}
            for k, v in state.items():
                try:
                    input_state[k] = copy.deepcopy(v)
                except Exception:
                    input_state[k] = v

            print(f"\n================ [DEBUG] ENTERING NODE: {node_name} ================")
            print("--- INPUT STATE ---")
            print(json.dumps(input_state, default=safe_serialize, indent=2))

            # Execute actual graph node handler
            output_updates = func(state, *args, **kwargs)

            print("--- OUTPUT STATE UPDATES ---")
            print(json.dumps(output_updates, default=safe_serialize, indent=2))

            # Detect differences / modifications
            added_fields = []
            modified_fields = []
            for k, v in output_updates.items():
                if k not in input_state:
                    added_fields.append(k)
                else:
                    if safe_serialize(input_state[k]) != safe_serialize(v):
                        modified_fields.append(k)

            print("--- DELTA ASSESSMENT ---")
            print(f"Added Fields: {added_fields}")
            print(f"Modified Fields: {modified_fields}")
            print(f"Tools Executed: {list(executed_tools_in_session)}")
            print(f"================ [DEBUG] LEAVING NODE: {node_name} ================\n")

            return output_updates
        return wrapper
    return decorator
