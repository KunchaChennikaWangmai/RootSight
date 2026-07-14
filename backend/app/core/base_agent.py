from typing import Callable, Any, Dict, List
from app.api.schemas import AnalysisFinding

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
        return tool.run(*args, **kwargs)
