
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

