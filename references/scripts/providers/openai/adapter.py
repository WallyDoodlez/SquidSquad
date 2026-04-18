"""OpenAI provider adapter — handles API calls with tool-use loop."""

import json
import os
import sys
import time


def _ensure_openai():
    """Lazy import openai, auto-install if missing."""
    try:
        import openai
        return openai
    except ImportError:
        import subprocess
        print("[model_router] Installing openai package...", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "openai>=1.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import openai
        return openai


def call(model, system_prompt, user_prompt, tools, tool_handler, timeout=120):
    """Call OpenAI API with tool-use loop.

    Args:
        model: Model name (e.g. "gpt-5.2")
        system_prompt: System message content
        user_prompt: User message content
        tools: List of tool definitions in OpenAI function-calling format
        tool_handler: Callable(name, args) -> str that executes tool calls
        timeout: API timeout in seconds

    Returns:
        Final text response from the model.

    Raises:
        RuntimeError on API failure.
    """
    openai = _ensure_openai()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")

    client = openai.OpenAI(api_key=api_key, timeout=timeout)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    max_iterations = 50  # safety cap on tool-use loop
    for _ in range(max_iterations):
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": 32768,
            "temperature": 0.2,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

        choice = response.choices[0]

        # If no tool calls, return the text
        if not choice.message.tool_calls:
            return choice.message.content or ""

        # Process tool calls
        messages.append(choice.message)
        for tc in choice.message.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            result = tool_handler(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    raise RuntimeError("Tool-use loop exceeded max iterations (50)")
