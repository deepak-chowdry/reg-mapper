import os
import uuid
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

def upload_to_cloudflare(local_filename: str) -> str:
    """
    Upload a file to Cloudflare R2 storage.
    
    Args:
        local_filename: Path to the local file to upload
        
    Returns:
        URL of the uploaded file
    """
    unique_id = str(uuid.uuid4())
    upload_url = os.environ["CLOUDFLARE_API_URL"] + unique_id + ".json"
        
    with open(local_filename, 'rb') as f:
        headers = {'Content-Type': 'application/' + "json"}
        upload_response = requests.put(upload_url, data=f.read(), headers=headers)
        upload_response.raise_for_status()
    
    new_url = f"{os.environ['CLOUDFLARE_CDN_URL']}{unique_id}.json"
    return new_url


def clean_up_file(file_path: str) -> None:
    """Delete a file if it exists."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting {file_path}: {e}")

    