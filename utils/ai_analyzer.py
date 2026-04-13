import os
import requests
import json
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
    
    def analyze_line(self, line: str, max_retries: int = 3) -> Dict:
        """
        Step 2: Generate AI keywords for a script line using DeepSeek model
        """
        prompt = f"""Analyze this script line and generate visual search keywords for stock video footage.

Script line: "{line}"

Return ONLY a JSON object with:
{{
  "line": "{line}",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "subject": "main subject",
  "mood": "scene mood",
  "stock_query": "best stock video search query"
}}

Make keywords highly visual and semantic. Focus on what should be shown on screen."""

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek/deepseek-chat",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Parse JSON response
                    analysis = json.loads(content)
                    logger.info(f"Successfully analyzed: {line}")
                    return analysis
                
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON response, retrying...")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Error analyzing line: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        # Fallback response
        logger.warning(f"Failed to analyze {line} after retries, using fallback")
        return {
            "line": line,
            "keywords": ["generic", "professional", "video"],
            "subject": "general",
            "mood": "neutral",
            "stock_query": line
        }
