from llm import get_client

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for business information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

response = get_client().chat.completions.create(
    model="gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Find information about healthy meal delivery demand among college students in Kochi."
        }
    ],
    tools=tools,
    tool_choice="auto"
)

message = response.choices[0].message

print("Content:")
print(message.content)

print("\nTool calls:")
print(message.tool_calls)