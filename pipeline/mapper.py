import json
import os
import logging
from dotenv import load_dotenv
from litellm import completion

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def map_chapters(document_content, chapter_content):
    # Check if API key is available
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        return {
            "error": "API key not found. Please set OPENROUTER_API_KEY in your .env file",
            "status": "authentication_error"
        }
    prompt = f"""Analyze document relevance to specific CPC Ireland chapter.

    DOCUMENT DETAILS:
    {document_content}

    CPC IRELAND CHAPTER:
    {chapter_content}

    RELEVANCE ASSESSMENT:
    Rate the relevance of this document to the CPC Ireland chapter (0.0-1.0):
    - 0.0: No relevance - document doesn't relate to this chapter's requirements
    - 0.3-0.4: Minimal relevance - some tangential connection
    - 0.5-0.6: Moderate relevance - document addresses some chapter requirements
    - 0.7-0.8: High relevance - document directly addresses key chapter requirements
    - 0.9-1.0: Very high relevance - document primarily focused on chapter requirements

    FORMAT OF MAPPED REQUIREMENTS:
    For mapped_requirements, use structured identifiers in format: "section-section_id_chapter-chapter_num_part-part_num"
    Example: "section-16_chapter-1_part-1" for section 16 in chapter 1 of part 1
    If multiple sections are relevant, list them as separate array items.
    If no specific sections are relevant, use ["None"].

    REQUIRED OUTPUT FORMAT (JSON):
    {{
    "relevance_score": "0.0-1.0",
    "relevance_reasoning": "reason here",
    "confidence_level": "high/medium/low",
    "mapped_requirements": ["section-16_chapter-1_part-1", "section-17_chapter-1_part-1"] or ["None"],
    "is_relevant": "yes/no"
    }}"""

    messages = [
        {"role": "system", "content": "You are an expert in Irish consumer protection compliance analysis."},
        {"role": "user", "content": prompt}
    ]

    response = completion(
        model="openrouter/openai/gpt-4o-mini",
        messages=messages,
        temperature=0.1
    )

    try:
        output_text = response["choices"][0]["message"]["content"]
        
        # Strip markdown code blocks if present
        if output_text.strip().startswith('```'):
            # Find the first occurrence of newline after ```
            start_idx = output_text.find('\n') + 1
            # Find the last occurrence of ```
            end_idx = output_text.rfind('```')
            if start_idx > 0 and end_idx > start_idx:
                output_text = output_text[start_idx:end_idx].strip()
        
        result = json.loads(output_text)
        logger.info(f"Is relevant {result.get('is_relevant', 'None')}")
    except Exception as e:
        result = {
            "error": str(e),
            "raw_output": response["choices"][0]["message"]["content"],
        }

    return result
