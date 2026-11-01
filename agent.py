
import json


from tools import search_web
from calculations import calculate_financials

from llm import get_client






def ask_ai(question):
    
    search_count = 0
    MAX_SEARCHES = 3
    
    tools = [
        {
        "type" : "function",
        "function" : 
            {
            "name" : "search_web",
            "description" : "Search the web for information about a business, competitors, prices, customers, or market conditions.",
            "parameters" : 
                {
                "type" : "object",
                "properties": 
                    {
                    "query" : {
                        "type": "string",
                        "description" : "The search query to use."
                        }
                    },
                    "required":["query"]
                }
            }
        },
        {
            "type":"function",
            "function" : {
                "name" : "calculate_financials",
                "description" : "Calculate contribution per unit and break-even units for a business.",
                "parameters" : {
                        "type" : "object",
                        "properties" : {
                            "price" : {
                                "type" : "number",
                                "description" : "Selling price per unit."
                            },
                            "variable_cost" : {
                                "type" : "number",
                                "description" : "Variable cost per unit."
                            },
                            "fixed_cost": {
                            "type": "number",
                            "description": "Total fixed costs."  
                            }                          
                        },
                        "required" : [
                            "price",
                            "variable_cost",
                            "fixed_cost"
                            ]
                    }
                }
            }
    ]

    messages=[
        {
            "role" : "user",
            "content" : question
        }
    ]
    
    for _ in range(8):
        
        
        response = get_client().chat.completions.create(
            model="auto",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
            
        response_message =  response.choices[0].message  

        if not response_message.tool_calls:
            
            structured_response = response_message.content
            
            return structured_response
        
        messages.append(response_message)
        
        
        for tool_call in response_message.tool_calls:
            
            tool_name = tool_call.function.name
            
            if tool_name not in [
                "search_web",
                "calculate_financials"
            ]:
                print(f"Unknown tool reqiured : {tool_name}")
                continue
            
            
            if tool_name == "search_web":
                
                try:

                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                except json.JSONDecodeError:

                    print("\nInvalid tool arguments received from the model.")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (
                                "The tool arguments were invalid JSON. "
                                "Please generate the search_web tool call again "
                                "with valid JSON."
                            )
                        }
                    )

                    continue
                            
                if search_count >= MAX_SEARCHES : 
                    
                    messages.append(
                        {
                            "role" : "tool",
                            "tool_call_id" : tool_call.id,
                            "content" : (
                                "Research limit reached. "
                                "Stop searching and return the final JSON now."
                            )
                        }
                    )
                
                    continue
                
                query = arguments.get("query")

                if not query:
                    print("\nSearch tool called without a query.")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": (
                                "The search_web tool requires a non-empty 'query' argument. "
                                "Please call search_web again with a valid query."
                            )
                        }
                    )
                    continue

                search_count += 1
                result = search_web(query)
                messages.append(
                    {
                        "role" : "tool",
                        "tool_call_id" : tool_call.id,
                        "content" : result
                    }
                )
                
                
            elif tool_name == "calculate_financials":
                
                arguments = json.loads(
                    tool_call.function.arguments
                )
                
                result = calculate_financials(
                    price = arguments["price"],
                    variable_cost=arguments["variable_cost"],
                    fixed_cost=arguments["fixed_cost"]
                )
                messages.append(
                    {
                        "role" : "tool",
                        "tool_call_id" : tool_call.id,
                        "content" : str(result)
                    }
                )  
                        
    
    return "The agent reached its research limit."