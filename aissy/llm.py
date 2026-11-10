
def generate_response(messages, llm):
    if not isinstance(messages, list):
        raise TypeError("Messages must be a list.")

    if not messages:
        raise ValueError("Messages cannot be empty.")

    for message in messages:
        if not isinstance(message, dict):
            raise TypeError("Each message must be a dictionary.")

        if "role" not in message or "content" not in message:
            raise ValueError("Each message must have role and content.")

        if message["role"] not in ("system", "user", "assistant"):
            raise ValueError("Invalid message role.")

        if not isinstance(message["content"], str):
            raise TypeError("Message content must be a string.")

    response = llm.generate(messages)

    if not isinstance(response, str):
        raise TypeError("LLM response must be a string.")

    if not response.strip():
        raise ValueError("LLM response cannot be empty.")

    return {
        "role": "assistant",
        "content": response
    }


def generate_response_with_tools(messages, llm, tools):
    if not isinstance(messages, list):
        raise TypeError("Messages must be a list.")

    if not messages:
        raise ValueError("Messages cannot be empty.")

    if not isinstance(tools, list):
        raise TypeError("Tools must be a list.")

    response = llm.generate_with_tools(messages, tools)

    if not isinstance(response, dict):
        raise TypeError("LLM tool response must be a dictionary.")

    if response.get("role") != "assistant":
        raise ValueError("LLM tool response must have assistant role.")

    content = response.get("content")
    tool_calls = response.get("tool_calls", [])

    if content is not None and not isinstance(content, str):
        raise TypeError("LLM response content must be a string or None.")

    if not isinstance(tool_calls, list):
        raise TypeError("Tool calls must be a list.")

    if not tool_calls and (not content or not content.strip()):
        raise ValueError("LLM response cannot be empty.")

    for call in tool_calls:
        if not isinstance(call, dict):
            raise TypeError("Each tool call must be a dictionary.")

        function = call.get("function")

        if not isinstance(function, dict):
            raise ValueError("Tool call must contain a function.")

        if not isinstance(function.get("name"), str):
            raise ValueError("Tool call must have a function name.")

        arguments = function.get("arguments")

        if not isinstance(arguments, str):
            raise TypeError("Tool arguments must be a JSON string.")

    return {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls
    }
