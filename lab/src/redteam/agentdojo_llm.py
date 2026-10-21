"""AgentDojo's agent, with every model call sent through the engagement harness.

AgentDojo's own OpenAILLM uses Chat Completions, which does not allow tools with reasoning
on current models, and retries on any error, so a Stop from the harness would be retried.
This element calls the Responses API through the harness instead.
"""

import json
import re
from collections.abc import Callable, Sequence
from typing import Any

from agentdojo.agent_pipeline import AgentPipeline, InitQuery, SystemMessage, ToolsExecutionLoop, ToolsExecutor
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.attacks import load_attack
from agentdojo.attacks.base_attacks import BaseAttack, FixedJailbreakAttack
from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.task_suite.task_suite import TaskSuite
from agentdojo.types import ChatAssistantMessage, ChatMessage, get_text_content_as_str, text_content_block_from_string


def _tool(f: Function) -> dict:
    return {"type": "function", "name": f.name, "description": f.description, "parameters": f.parameters.model_json_schema(), "strict": False}


class GuardedLLM(BasePipelineElement):
    def __init__(self, call_model: Callable[..., Any]) -> None:
        self.call_model = call_model
        self.last_messages: Sequence[ChatMessage] = []
        # Storage is off, so the model's reasoning and calls are sent back each turn, keyed by call ID.
        self.output_items: dict[str, list[dict]] = {}

    def _input(self, messages: Sequence[ChatMessage]) -> list[dict]:
        items: list[dict] = []
        for m in messages:
            text = get_text_content_as_str(m["content"] or [])
            match m["role"]:
                case "system":
                    items.append({"role": "developer", "content": text})
                case "user":
                    items.append({"role": "user", "content": text})
                case "assistant" if m["tool_calls"]:
                    items.extend(self.output_items[m["tool_calls"][0].id])
                case "assistant":
                    items.append({"role": "assistant", "content": text})
                case "tool":
                    items.append({"type": "function_call_output", "call_id": m["tool_call_id"], "output": m["error"] or text})
        return items

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        tools = [_tool(f) for f in runtime.functions.values()]
        response = self.call_model(input=self._input(messages), **({"tools": tools} if tools else {}))
        calls = [
            FunctionCall(function=item.name, args=json.loads(item.arguments or "{}"), id=item.call_id)
            for item in response.output
            if item.type == "function_call"
        ]
        if calls:
            self.output_items[calls[0].id] = [item.model_dump(exclude_none=True) for item in response.output]
        text = response.output_text
        reply = ChatAssistantMessage(
            role="assistant", content=[text_content_block_from_string(text)] if text else None, tool_calls=calls or None
        )
        messages = [*messages, reply]
        self.last_messages = messages
        return query, runtime, env, messages, extra_args


def pipeline(call_model: Callable[..., Any], model: str) -> tuple[AgentPipeline, GuardedLLM]:
    """AgentDojo's default agent, with no defence: the system message, the query, then the tool loop."""
    llm = GuardedLLM(call_model)
    agent = AgentPipeline(
        [SystemMessage(load_system_message(None)), InitQuery(), llm, ToolsExecutionLoop([ToolsExecutor(), llm])]
    )
    agent.name = model
    return agent, llm


def attack(name: str, suite: TaskSuite, agent: AgentPipeline, model: str) -> BaseAttack:
    """AgentDojo's attacks. important_instructions addresses the model by name, and AgentDojo's
    list of names stops at older models, so the name is worked out from the model ID here."""
    if name != "important_instructions":
        return load_attack(name, suite, agent)
    found = re.match(r"gpt-(\d+(?:\.\d+)?)", model)
    attack = ImportantInstructionsAttack.__new__(ImportantInstructionsAttack)
    FixedJailbreakAttack.__init__(attack, ImportantInstructionsAttack._JB_STRING, suite, agent)
    attack.user_name = "Emma Johnson"
    attack.model_name = f"GPT-{found.group(1)}" if found else "AI assistant"
    return attack
