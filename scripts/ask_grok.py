import requests
import os
import sys
from openai import OpenAI
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)
load_dotenv('.env', override=True)

from api.logger import Logger
log = Logger('ask-grok')

class WebSearchRequest(BaseModel):
    query: str = Field(description="The search query")

class GetWebpageRequest(BaseModel):
    url: str = Field(description="The URL of the webpage to fetch")

class ExtractTextRequest(BaseModel):
    html: str = Field(description="The HTML content to parse")
    selector: str = Field(description="The CSS selector to use")

class FindPatternsRequest(BaseModel):
    text: str = Field(description="The text to search within")
    pattern: str = Field(description="The regular expression pattern to match")

class ExtractStructuredDataRequest(BaseModel):
    html: str = Field(description="The HTML content to parse")

class AskGrokSync:
    def __init__(self, api_key: str = None, client: OpenAI = None):
        if not api_key:
            try:
                log.debug(f"API key not provided. Checking environment variable.")
                api_key = os.getenv("XAI_API_KEY")
                if api_key:
                    log.debug(f"API key {api_key} found in environment variable.")
            except KeyError as e:
                log.critical(f"API key is required.: {e}")

        if not client:
            log.info("Creating new OpenAI client.")
            self.client = OpenAI(api_key=api_key, base_url='https://api.xai.com/v1')
    
    def send_request(self, request: str, functions: List[Dict]=None) -> dict:
        """Send a single request to xAI with optional function calling."""
        return self.client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request}
            ],
            tools=functions,
            tool_choice="auto"
        )
    
    def process_requests(self, requests: List[str], functions: List[Dict]=None) -> List[dict]:
        """Process multiple requests sequentially with optional function calling."""
        return [self.send_request(request, functions) for request in requests]

def search_web(**kwargs) -> List[Dict[str, str]]:
    """
    Searches the web for the given query and returns a list of results,
    each with 'title', 'url', and 'snippet'.

    Args:
        query (str): The search query string.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing 'title', 'url', and 'snippet'.
    """
    request = WebSearchRequest(**kwargs)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    url = f"https://www.google.com/search?q={request.query}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        for g in soup.find_all('div', class_='g'):
            title = g.find('h3')
            url = g.find('cite')
            snippet = g.find('div', class_='s')
            if title and url and snippet:
                results.append({
                    'title': title.text,
                    'url': url.text,
                    'snippet': snippet.text
                })
        return results[:10]  # Limit to top 10 results
    except Exception as e:
        print(f"Error in search_web: {e}")
        return []

def get_webpage(**kwargs) -> str:
    """
    Retrieves the HTML content of the specified URL.

    Args:
        url (str): The URL of the webpage to fetch.

    Returns:
        str: The HTML content of the webpage.
    """
    request = GetWebpageRequest(**kwargs)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()
        return { "html": response.text }
    except Exception as e:
        print(f"Error in get_webpage: {e}")
        return { "html": "" }

def extract_text(**kwargs) -> str:
    """
    Extracts text from the HTML using the given CSS selector.

    Args:
        html (str): The HTML content to parse.
        selector (str): The CSS selector to locate the desired element.

    Returns:
        str: The extracted text, or an empty string if no match is found.
    """
    request = ExtractTextRequest(**kwargs)
    try:
        soup = BeautifulSoup(request.html, 'html.parser')
        element = soup.select_one(request.selector)
        return { "text": element.text.strip() if element else "" }
    except Exception as e:
        print(f"Error in extract_text: {e}")
        return { "text": "" }

def find_patterns(**kwargs) -> List[str]:
    """
    Finds all occurrences of the regex pattern in the text.

    Args:
        text (str): The text to search within.
        pattern (str): The regular expression pattern to match.

    Returns:
        List[str]: A list of all matches found.
    """
    request = FindPatternsRequest(**kwargs)
    try:
        return { "matches": re.findall(request.pattern, request.text) }
    except Exception as e:
        print(f"Error in find_patterns: {e}")
        return { "matches": [] }

def extract_structured_data(**kwargs) -> Dict:
    """
    Extracts structured data (JSON-LD) from the HTML.

    Args:
        html (str): The HTML content to parse.

    Returns:
        Dict: The first valid JSON-LD object found, or an empty dictionary if none.
    """
    request = ExtractStructuredDataRequest(**kwargs)
    try:
        soup = BeautifulSoup(request.html, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.text)
                if isinstance(data, dict):
                    return { "data": data }
            except json.JSONDecodeError:
                continue
        return {}
    except Exception as e:
        print(f"Error in extract_structured_data: {e}")
        return {}
    
search_web_schema = WebSearchRequest.model_json_schema()
get_webpage_schema = GetWebpageRequest.model_json_schema()
extract_text_schema = ExtractTextRequest.model_json_schema()
find_patterns_schema = FindPatternsRequest.model_json_schema()
extract_structured_data_schema = ExtractStructuredDataRequest.model_json_schema()

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Performs a general web search",
            "parameters": search_web_schema,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_webpage",
            "description": "Fetches the HTML content of a webpage",
            "parameters": get_webpage_schema,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_text",
            "description": "Extracts text from HTML using a CSS selector",
            "parameters": extract_text_schema,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_patterns",
            "description": "Finds all occurrences of a regex pattern in text",
            "parameters": find_patterns_schema,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_structured_data",
            "description": "Extracts structured data (JSON-LD) from HTML",
            "parameters": extract_structured_data_schema,
        },
    },
]

def main() -> None:
    log.info("Starting main function.")
    """Main function to handle requests and display responses."""

    requests = [
        "Find information about Google",
        "Search for articles about AI",
        "Get the content of the OpenAI website",
        "Extract the title from the OpenAI website",
        "Find all email addresses on the OpenAI website",
        "Extract structured data from the OpenAI website"
    ]

    request = "Find information about the owner of Findlay Roofing in Atlanta. I need a name, phone number, and email address."

    provider = AskGrokSync()

    # This starts processing all asynchronously, but only 2 at a time
    # Instead of waiting for each request to finish before starting the next,
    # we can have 2 requests running at once, making it faster overall
    response = provider.send_request(requests, functions=tools_definition)
    if response:
        try:
            log.debug(f"Response: {response.choices[0].message.content}")
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    log.debug(f"Calling function {function_name} with arguments: {arguments}")
                    result = globals()[function_name](**arguments)
                    log.info(f"Function {function_name} returned: {result}")
        except AttributeError as e:
            log.error(f"Error processing response: {e}")
        except Exception as e:
            log.error(f"Unexpected error processing response: {e}")

if __name__ == "__main__":
    main()