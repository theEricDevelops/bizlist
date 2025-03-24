import requests
import asyncio
import os
import sys
from asyncio import Semaphore
from openai import AsyncOpenAI, AsyncClient
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin
from typing import List, Dict, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)
load_dotenv('.env', override=True)

from api.logger import Logger
log = Logger('ask-grok')

log.debug(f"Environment variables: {os.environ}")

class CompanyWebSearch(BaseModel):
    name: str = Field(description="The name of the company to search for.")
    industry: str = Field(description="The industry or sector of the company.")
    location: str = Field(description="The location of the company.")
    phone: str = Field(description="The phone number of the company.")
    website: str = Field(description="The website of the company.")

class ContactWebSearch(BaseModel):
    name: str = Field(description="The name of the person to search for.")
    company: str = Field(description="The company the person works for.")
    title: str = Field(description="The job title of the person.")
    location: str = Field(description="The location of the person.")
    email: str = Field(description="The email address of the person.")
    linkedin: str = Field(description="The LinkedIn profile URL of the person.")

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

class AskGrok:
    def __init__(self, api_key: str= None, client: AsyncClient = None):
        if not api_key:
            try:
                log.debug(f"API key not provided. Checking environment variable.")
                api_key = os.getenv("XAI_API_KEY")
                if api_key:
                    log.debug(f"API key {api_key} found in environment variable.")
            except KeyError:
                log.critical("API key is required.")
                raise ValueError("API key is required.")
        if not client:
            log.info("Creating new OpenAI client.")
            self.client = AsyncOpenAI(api_key=api_key)

    async def send_request(self, sem: Semaphore, request: str, functions: List[Dict]=None) -> dict:
        """Send a single request to xAI with semaphore control and optional function calling."""
        async with sem:
            return await self.client.chat.completions.create(
                model="grok-2-latest",
                messages=[{"role": "user", "content": request}],
                tools=functions,
                tool_choice="auto"
            )

    async def process_requests(self, requests: List[str], functions: List[Dict]=None, max_concurrent: int = 2) -> List[dict]:
        """Process multiple requests with controlled concurrency and optional function calling."""
        # Create a semaphore that limits how many requests can run at the same time
        # Think of it like having only 2 "passes" to make requests simultaneously
        sem = Semaphore(max_concurrent)

        # Create a list of tasks (requests) that will run using the semaphore
        tasks = [self.send_request(sem, request, functions) for request in requests]

        # asyncio.gather runs all tasks in parallel but respects the semaphore limit
        # It waits for all tasks to complete and returns their results
        return await asyncio.gather(*tasks)


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

async def main() -> None:
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

    provider = AskGrok()
    log.debug(f"Processing {len(requests)} requests with {provider}.")

    # This starts processing all asynchronously, but only 2 at a time
    # Instead of waiting for each request to finish before starting the next,
    # we can have 2 requests running at once, making it faster overall
    responses = await provider.process_requests(requests, functions=tools_definition)

    # Print each response in order
    for i, response in enumerate(responses):
        log.debug(f"# Response {i}:")
        log.debug(f"Response: {response.choices[0].message.content}")
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                log.debug(f"Calling function {function_name} with arguments: {arguments}")
                result = globals()[function_name](**arguments)
                log.info(f"Function {function_name} returned: {result}")

if __name__ == "__main__":
    asyncio.run(main(), debug=True)