import json
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    
    with open("all_chapters.json", "r", encoding="utf-8") as f:
        chapter_data = json.load(f)


    logger.info(f"Total {len(chapter_data)} parts")
    # Prepare all chapter tasks for parallel processing
    chapter_tasks = []
    all_chapters_info = []  # Track all chapters from all parts
    for part in chapter_data:
        part_num = part.get("Part", "None")
        part_title = part.get("Title", "None")
        chapters = part.get("chapters", [])

        logger.info(f"Mapping {len(chapters)} chapters...")
        
        for chapter in chapters:
            chapter_content = structure_chapters_content(chapter, part_num, part_title)
            chapter_num = chapter.get('chapter_num', 'Unknown')
            chapter_tasks.append((chapter_content, chapter_num, part_num))
            # Store all chapter info for later use
            all_chapters_info.append({
                "part_num": part_num,
                "chapter_num": chapter_num,
                "chapter_title": chapter.get('chapter_title', 'Unknown')
            })
    
    def process_chapter(chapter_data_tuple):
        chapter_content, chapter_num, part_num = chapter_data_tuple
        return map_chapters(chapter_content, document_content, chapter_num, part_num)
    
    # Process chapters in parallel using ThreadPoolExecutor
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_chapter = {executor.submit(process_chapter, task): task for task in chapter_tasks}
        
        # Collect results as they complete
        for future in as_completed(future_to_chapter):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                chapter_task = future_to_chapter[future]
                logger.error(f"Error processing chapter {chapter_task[1]}: {e}")
    
    logger.info(f"Completed parallel processing of {len(results)} chapters")
    
    relevant_chapters = []
    all_mapped_chapters = []  # Chapters mapped from relevant chapters only
    for result in results:
        try:
            is_relevant = result.get("is_relevant", False)
            if is_relevant:
                relevant_chapters.append(result)
                # Collect mapped_chapters only from relevant chapters
                if "mapped_chapters" in result and result["mapped_chapters"] != ["None"]:
                    all_mapped_chapters.extend(result["mapped_chapters"])
        except Exception as e:
            logger.warning(f"Error processing result: {e}")
    
    logger.info(f"Saving results...")
    logger.info(f"Total chapters processed: {len(results)}")
    logger.info(f"Relevant chapters: {len(relevant_chapters)}")
    logger.info(f"Mapped chapters from relevant results: {len(all_mapped_chapters)}")
    
    # Combine everything into a single JSON structure
    combined_results = {
        "summary": {
            "total_chapters_processed": len(results),
            "relevant_chapters_count": len(relevant_chapters),
        },
        "all_mapped_chapters": all_mapped_chapters,
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
