"""
Minimal Agent base class, deliberately shaped to mirror Google's Agent
Development Kit (ADK) primitives used in the Vibe Coding course:

  - `name` / `instructions`: identity + system behavior of the agent
  - `tools`: a dict of callables the agent is allowed to invoke
  - `run(event, context)`: the single entrypoint the orchestrator calls

This keeps the demo runnable with zero extra dependencies while making
it a near drop-in port to `google.adk.Agent` — swap this base class for
the real ADK Agent, keep `tools` as-is, and move `run()`'s logic into an
ADK planner/tool-calling loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Agent:
    name: str
    instructions: str
    tools: dict[str, Callable] = field(default_factory=dict)

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise KeyError(f"Agent '{self.name}' has no tool named '{tool_name}'")
        return self.tools[tool_name](**kwargs)

    def run(self, event: dict, context: dict | None = None) -> dict:  # pragma: no cover
        raise NotImplementedError
