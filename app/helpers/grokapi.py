# /api/helpers/grokapi.py
import os, sys, json, requests
from typing import Dict, List

# Add the root directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.logger import Logger
from app.helpers.aitools import search_web, get_webpage, extract_text, find_patterns, extract_structured_data, tools_definition
from app.schemas import OwnerSearchSchema

# Initialize the logger
log = Logger('helper-grok-api')

class AskGrok:
    def __init__(self, api_key: str = None):
        if not api_key:
            try:
                log.debug(f"API key not provided. Checking environment variable.")
                api_key = os.getenv("XAI_API_KEY")
                if api_key:
                    log.debug(f"API key found in environment variable.")
                else:
                    log.critical("API key is required and not found in environment variable.")
                    raise ValueError("API key is required and not found in environment variable.")
            except KeyError as e:
                log.critical(f"API key is required.: {e}")
                raise

        self.api_key = api_key
        self.base_url = 'https://api.x.ai/v1/chat/completions'
        self.chat_history = []
        self.html_content_cache = {}  # Add a cache for HTML content
        self.max_history_length = 10  # Limit chat history length
        self.tools = tools_definition

    def _send_request(self, request: str, functions: List[Dict]=None) -> dict:
        """Send a single request to xAI with optional function calling."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        system_message = f"""
            You are a web scraping expert. You will receive a JSON with any combination of the following company information:

            - company_name: string
            - phone: string (company phone)
            - email: string (company email)
            - address: string (company address)
            - website: string (company website)
            - industry: string (company industry)

            Your task is to search the web to complete the remaining fields and to attempt to find the owner's information.

            You have access to the following functions:
            - search_web(query: str) -> List[Dict[str, str]]: Searches the web for the query and returns a list of results, each with 'title', 'url', and 'snippet'.
            - get_webpage(url: str) -> str: Retrieves the HTML content of the URL.
            - extract_text(html: str, selector: str) -> str: Extracts text from the HTML using the CSS selector.
            - find_patterns(text: str, pattern: str) -> List[str]: Finds all matches of the regex pattern in the text.
            - extract_structured_data(html: str) -> Dict: Extracts structured data (JSON-LD or microdata) from the HTML.

            Use these functions to gather the required information.

            The final output must be in JSON schema. 
            
            {OwnerSearchSchema.model_json_schema()}
            
            If you cannot find a particular piece of information, set its value to null.
        """

        # Build the messages payload including chat history
        messages = [{"role": "system", "content": system_message}]
        
        # Add filtered chat history (excluding HTML content)
        filtered_history = self._filter_chat_history()
        messages.extend(filtered_history)
        
        # Add current request
        messages.append({"role": "user", "content": request})

        payload = {
            "messages": messages,
            "model": "grok-2-latest",
            "stream": False,
            "temperature": 0,
        }

        if functions:
            payload["tools"] = functions
            payload["tool_choice"] = "auto"

        log.debug(f"Sending request to {self.base_url} with payload: {payload}")
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()  # Raise an exception for bad status codes
            log.debug(f"Response: {response.json()}")
            
            # Update chat history
            response_data = response.json()
            if 'choices' in response_data and response_data['choices']:
                assistant_message = response_data['choices'][0]['message']
                
                # Limit chat history length
                if len(self.chat_history) >= 2 * self.max_history_length:
                    self.chat_history = self.chat_history[-2 * self.max_history_length:]
                
                self.chat_history.append({"role": "user", "content": request})
                self.chat_history.append(assistant_message)

            return response_data
        except requests.exceptions.RequestException as e:
            log.error(f"Error sending request: {e}")
            return {}
        except json.JSONDecodeError as e:
            log.error(f"Error decoding JSON response: {e}")
            return {}

    def _filter_chat_history(self):
        """Filter the chat history to remove HTML content and limit its size."""
        filtered_history = []
        
        for message in self.chat_history:
            # Skip messages with very large content (likely HTML)
            if isinstance(message.get('content'), str) and len(message.get('content', '')) > 10000:
                # Replace with a summary
                filtered_message = message.copy()
                filtered_message['content'] = f"[Large content summary - {len(message['content'])} characters]"
                filtered_history.append(filtered_message)
            elif 'tool_calls' in message:
                # Process tool calls to remove HTML content
                filtered_message = message.copy()
                if 'tool_calls' in filtered_message:
                    for tool_call in filtered_message['tool_calls']:
                        if 'function' in tool_call and 'arguments' in tool_call['function']:
                            args = json.loads(tool_call['function']['arguments'])
                            # Replace HTML content with a placeholder
                            if 'html' in args and len(args['html']) > 5000:
                                html_id = f"html_{id(args['html'])}"
                                self.html_content_cache[html_id] = args['html']
                                args['html'] = f"[HTML content cached with id: {html_id}]"
                                tool_call['function']['arguments'] = json.dumps(args)
                filtered_history.append(filtered_message)
            else:
                filtered_history.append(message)
                
        return filtered_history
    
    def ask(self, request: str, functions: List[Dict]=None) -> dict:
        # Initial request
        response = self._send_request(request, functions=tools_definition)
        
        # Process the response with improved error handling and timeouts
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while response and iteration < max_iterations:
            iteration += 1
            try:
                if 'choices' in response and response['choices'] and 'message' in response['choices'][0]:
                    message = response['choices'][0]['message']
                    finish_reason = response['choices'][0].get('finish_reason')

                    # If the AI wants to use tools
                    if finish_reason == 'tool_calls' and 'tool_calls' in message:
                        log.info("AI requested to use tools.")
                        # Process all tool calls in the current response
                        tool_results = []
                        for tool_call in message['tool_calls']:
                            function_name = tool_call['function']['name']
                            arguments = json.loads(tool_call['function']['arguments'])
                            
                            # Check for cached HTML content
                            if function_name == 'extract_text' and 'html' in arguments:
                                html_ref = arguments.get('html')
                                if isinstance(html_ref, str) and html_ref.startswith('[HTML content cached with id:'):
                                    html_id = html_ref.split('id:')[1].strip()[:-1]
                                    if html_id in self.html_content_cache:
                                        arguments['html'] = self.html_content_cache[html_id]
                            
                            log.debug(f"Calling function {function_name} with arguments: {arguments}")
                            result = globals()[function_name](**arguments)
                            log.info(f"Function {function_name} returned: {result}")
                            tool_results.append({
                                "name": function_name,
                                "result": result
                            })
                        
                        # Send all tool results back to the AI
                        if tool_results:
                            result_str = json.dumps(tool_results)
                            follow_up_request = f"Here are the results from the tool calls: {result_str}. Please continue with the analysis."
                            response = self._send_request(follow_up_request, functions=tools_definition)
                        else:
                            break
                    elif finish_reason == 'stop':
                        # We got a final response
                        if 'content' in message and message['content']:
                            log.info(f"Final Response Received.")
                            log.debug(f"Final Response: {message['content']}")
                            return message['content']
                        else:
                            log.warning(f"Empty or missing content in response")
                        # Exit the loop since we're done
                        break
                    else:
                        log.warning(f"Unexpected finish_reason: {finish_reason}")
                        break
                else:
                    log.warning(f"Unexpected response format: {response}")
                    break
            except Exception as e:
                log.error(f"Error processing response: {e}")
                break
        