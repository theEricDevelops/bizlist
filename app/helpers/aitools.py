# /api/helpers/aitools.py
import os, sys, re, json
from pydantic import BaseModel, Field
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add the root directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv('.env')

from app.services.logger import Logger
from app.helpers.searchapi import SearchAPI
log = Logger('helper-grok-api')

class WebSearchRequest(BaseModel):
    query: str = Field(description="The search query")
    engine: str = Field(default="google", description="The search engine to use")

class GetWebpageRequest(BaseModel):
    url: str = Field(description="The URL of the webpage to fetch")

class ExtractTextRequest(BaseModel):
    html: str = Field(description="The HTML content to parse")
    selector: List[str] = Field(description="A list of CSS selectors to use")

class FindPatternsRequest(BaseModel):
    text: str = Field(description="The text to search within")
    pattern: str = Field(description="The regular expression pattern to match")

class ExtractStructuredDataRequest(BaseModel):
    html: str = Field(description="The HTML content to parse")

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
    search_api = SearchAPI()
    
    log.debug(f"Searching web with query: {request.query}")
    try:
        response: dict = search_api.search(request.query, request.engine)
        data = response.get('organic_results', {})
        
        results = []
        if data:
            for result in data:
                results.append({
                    "title": result.get('title', ''),
                    "url": result.get('link', ''),
                    "snippet": result.get('snippet', ''),
                    "source": result.get('source', ''),
                    "date": result.get('date', ''),
                    "sitelinks": result.get('sitelinks', [])
                })
        else:
            log.warning(f"No results found for query: {request.query}")
        return results
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
        log.debug(f"Fetching webpage: {request.url}")
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract just the relevant content instead of the full page
        # Remove script, style and other unnecessary elements
        for script in soup(["script", "style", "iframe", "noscript"]):
            script.decompose()
            
        page_body = soup.body.text.strip()
        
        # Limit the size of returned HTML
        max_size = 50000
        if len(page_body) > max_size:
            log.warning(f"HTML content truncated from {len(page_body)} to {max_size} characters")
            page_body = page_body[:max_size] + "\n[Content truncated due to size...]"
            
        return { "html": page_body }
    except Exception as e:
        log.error(f"Error in get_webpage: {e}")
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
        elements = soup.select(request.selector)
        
        # Handle case where selector returns empty results
        if not elements:
            log.warning(f"Selector '{request.selector}' returned no results")
            
            # Try to suggest alternative selectors
            all_possible_elements = ['span', 'div', 'p', 'a', 'h1', 'h2', 'h3', 'h4']
            for element in all_possible_elements:
                samples = soup.select(element)
                if samples and len(samples) < 10:  # Don't suggest selectors that would return too many elements
                    log.info(f"Possible alternative selector: '{element}' would return {len(samples)} results")
            
            # If looking for phones specifically, try regex instead
            if 'phone' in request.selector.lower():
                phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
                phone_matches = re.findall(phone_pattern, request.html)
                if phone_matches:
                    return {"text": ", ".join(phone_matches)}
            
            return {"text": "", "error": f"Selector '{request.selector}' returned no results"}
            
        return {"text": "\n".join(element.text.strip() for element in elements)}
    except Exception as e:
        log.error(f"Error in extract_text: {e}")
        return {"text": "", "error": str(e)}

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