from ollama import chat
from geocode import geocode_location

MODEL = "qwen2.5:7b"

available_tools = {"geocode_location": geocode_location}


def run(user_prompt: str):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a location geocoding assistant. "
                "If the user's query mentions more than one place, "
                "call the geocode_location tool separately once for EACH place, "
                "one place name per call. Never combine multiple place names into a single call."
            )
        },
        {"role": "user", "content": user_prompt}
    ]

    response = chat(
        model=MODEL,
        messages=messages,
        tools=[geocode_location],
    )

    print("---- Model's first response ----")
    print(response.message)

    if response.message.tool_calls:
        messages.append(response.message)

        for tool_call in response.message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = tool_call.function.arguments
            print(f"\n>>> Model chose to call: {fn_name}({fn_args})")

            if fn_name in available_tools:
                result = available_tools[fn_name](**fn_args)
                print(f">>> Real tool output: {result}")

                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_name": fn_name,
                })

        # --- Fallback detection: sirf 1 call hui but lagta hai multiple jagah combine ho gayi ---
        if len(response.message.tool_calls) == 1:
            single_args = response.message.tool_calls[0].function.arguments
            single_place = single_args.get("place_name", "")
            comma_count = single_place.count(",")
            print(f"\n[DEBUG] Sirf 1 tool call hui. place_name = '{single_place}' (commas: {comma_count})")

        final_response = chat(model=MODEL, messages=messages)
        print("\n---- Final answer from model ----")
        print(final_response.message.content)
    else:
        print("\n(Model didn't call any tool — check prompt or try again)")


if __name__ == "__main__":
    while True:
        user_prompt = input("\nLocation query batao (ya 'exit' likho band karne ke liye): ")
        if user_prompt.strip().lower() == "exit":
            break
        run(user_prompt)