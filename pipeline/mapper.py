import json
import os
import logging
from typing import List
from dotenv import load_dotenv
from litellm import completion
import litellm
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress LiteLLM verbose logging
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)

# Disable LiteLLM proxy-related features that cause dependency issues
litellm.suppress_debug_info = True
litellm.drop_params = True
litellm.set_verbose = False

class Response(BaseModel):
    relevance_score: float = Field(
        description="Numeric score between 0.0 and 1.0 indicating how relevant the document is to the CPC Ireland chapter"
    )
    relevance_reasoning: str = Field(
        description="Brief explanation of why the relevance score was assigned"
    )
    confidence_level: str = Field(
        description="Confidence in the assessment: 'high', 'medium', or 'low'"
    )
    mapped_chapters: List[str] = Field(
        description="List of CPC Ireland chapter numbers relevant to the document, e.g., ['1', '2']; use ['None'] if none"
    )
    is_relevant: bool = Field(
        description="True if the document is relevant to the chapter, otherwise False"
    )

def map_chapters(document_content, chapter_content, chapter_num, part_num):
    # Check API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return {
            "error": "API key not found. Please set OPENROUTER_API_KEY in your .env file",
            "status": "authentication_error"
        }

    prompt = f"""
        You are an expert in Irish Consumer Protection Code (CPC) compliance.
        Your task is to determine how relevant the provided document is to the specified CPC Ireland chapter.
        Return output strictly as valid JSON matching the required schema.

        DOCUMENT CONTENT:
        {document_content}

        CPC IRELAND CHAPTER CONTENT:
        {chapter_content}

        SCORING GUIDE:
        - 0.0: No relevance
        - 0.3-0.4: Minimal relevance
        - 0.5-0.6: Moderate relevance
        - 0.7-0.8: High relevance
        - 0.9-1.0: Very high relevance

        RULES:
        - mapped_chapters must contain chapter numbers as strings, e.g., ["1"], ["1","2"], or ["None"]
        - is_relevant is True only if relevance_score >= 0.5
        - confidence_level must be one of: "high", "medium", "low"
        - Respond with JSON only — no extra text, no markdown

        REQUIRED JSON FORMAT:
        {{
            "relevance_score": 0.0,
            "relevance_reasoning": "string",
            "confidence_level": "high/medium/low",
            "mapped_chapters": ["1", "2"] or ["None"],
            "is_relevant": true/false
        }}
        """

    messages = [
        {"role": "system", "content": "You are a compliance analyst specializing in Irish CPC regulations. Always return strictly valid JSON following the given schema, without markdown or extra commentary."},
        {"role": "user", "content": prompt}
    ]

    response = completion(
        model="openrouter/openai/gpt-5-mini",
        messages=messages,
        temperature=0.1,
        response_format=Response
    )

    try:
        output_text = response["choices"][0]["message"]["content"].strip()
        
        # Remove markdown fencing if present
        if output_text.startswith("```"):
            start_idx = output_text.find("\n") + 1
            end_idx = output_text.rfind("```")
            if start_idx > 0 and end_idx > start_idx:
                output_text = output_text[start_idx:end_idx].strip()

        result = json.loads(output_text)
        logger.info(f"{part_num}  |  Chapter {chapter_num}  |  Is relevant: {result.get('is_relevant', 'None')}")
    except Exception as e:
        result = {
            "error": str(e),
            "raw_output": response["choices"][0]["message"]["content"],
        }

    return result
