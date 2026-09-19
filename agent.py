
import json


from tools import search_web
from calculations import calculate_financials

from llm import client
from research import evaluate_evidence






def ask_ai(question):
    
    search_count = 0
    MAX_SEARCHES = 6
    
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
            },
        {
            "type": "function",
            "function": {
                "name": "evaluate_evidence",
                "description": "Evaluate whether evidence actually supports or contradicts a business assumption.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "assumption": {
                            "type": "string",
                            "description": "The business assumption being investigated."
                        },
                        "evidence": {
                            "type": "string",
                            "description": "The evidence that should be evaluated."
                        }
                    },
                    "required": [
                        "assumption",
                        "evidence"
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
    
    for _ in range(15):
        
        
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages = messages,
            tools = tools,
            tool_choice = "auto"
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
                "calculate_financials",
                "evaluate_evidence"
            ]:
                print(f"Unknown tool reqiured : {tool_name}")
                continue
            
            
            if tool_name == "search_web":
                
                arguments = json.loads(
                    tool_call.function.arguments
                    )
                
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
                
                search_count +=1
                
                result = search_web(
                    arguments["query"]
                )
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
            
            elif tool_name == "evaluate_evidence":

                arguments = json.loads(
                    tool_call.function.arguments
                )

                result = evaluate_evidence(
                    assumption=arguments["assumption"],
                    evidence=arguments["evidence"]
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.model_dump_json()
                    }
                )               
    
    return "The agent reached its research limit."