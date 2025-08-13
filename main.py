import json
import logging
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from pipeline.cloudflare import clean_up_file, upload_to_cloudflare
from pipeline.mapper import map_chapters
from pipeline.structure_content import structure_chapters_content, structure_document_content

# Load environment variables
load_dotenv()

app = FastAPI(title="Regulation Mapper", description="API to map regulations")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class URLRequest(BaseModel):
    url: str

@app.post("/map-regulations")
async def process_json_url(request: URLRequest):
    """
    Endpoint that accepts a URL and returns a list of regulations
    """
    logger.info(f"Creating document structure...")
    document_content = structure_document_content(request.url)

    logger.info(f"Processing chapters...")
    with open("all_chapters.json", "r", encoding="utf-8") as f:
        chapter_data = json.load(f)

    results = []
    for part in chapter_data:
        part_num = part.get("Part", "None")
        part_title = part.get("Title", "None")
        chapters = part.get("chapters", [])

        for chapter in chapters:
            chapter_content = structure_chapters_content(chapter, part_num, part_title)
            logger.info(f"Processing chapter {chapter.get('chapter_num', 'Unknown')}...")
            response = map_chapters(chapter_content, document_content)

            results.append(response)
    
    relevant_chapters = []
    mapped_sections = []
    for result in results:
        try:
            is_relevant = result.get("is_relevant", "").lower()
            if is_relevant == "yes":
                relevant_chapters.append(result)
                if "mapped_requirements" in result and result["mapped_requirements"] != ["None"]:
                    mapped_sections.extend(result["mapped_requirements"])
        except Exception as e:
            logger.warning(f"Error processing result: {e}")
    
    logger.info(f"Saving results...")
    logger.info(f"Total chapters processed: {len(results)}")
    logger.info(f"Relevant chapters (score > 0.7): {len(relevant_chapters)}")
    logger.info(f"Total unique mapped sections: {len(mapped_sections)}")
    
    # Combine everything into a single JSON structure
    combined_results = {
        "summary": {
            "total_chapters_processed": len(results),
            "relevant_chapters_count": len(relevant_chapters),
            "mapped_sections_count": len(mapped_sections)
        },
        "all_mapped_sections": mapped_sections,
        "relevant_chapters": relevant_chapters,
    }
    
    # Create a temporary file path without keeping it open
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_file_path = temp_file.name
    temp_file.close()  # Close the file handle immediately
    
    # Save everything in a single JSON file
    logger.info(f"Saving results to {temp_file_path}")
    with open(temp_file_path, "w", encoding="utf-8") as f:
        json.dump(combined_results, f, indent=4)

    logger.info(f"Uploading results to cloudflare...")
    cloudflare_url = upload_to_cloudflare(temp_file_path)
    clean_up_file(temp_file_path)
    

    return {
        "status": "success",
        "data": cloudflare_url
    }


@app.get("/")
async def root():
    return {"message": "Regulation Mapper API is running"}
