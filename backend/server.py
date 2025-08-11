from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import hashlib
import io
from PIL import Image
import imagehash
import magic

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Image-to-URL Recognition App")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Image Processing Class
class ImageProcessor:
    def __init__(self):
        self.supported_formats = {'JPEG', 'PNG', 'GIF', 'BMP', 'WEBP'}
        self.max_dimension = 2048
        self.hash_size = 8
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_mime_types = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}
    
    async def validate_and_process_image(self, file: UploadFile) -> dict:
        """Validate and process uploaded image."""
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > self.max_file_size:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        
        # Validate MIME type using python-magic
        try:
            detected_type = magic.from_buffer(content, mime=True)
            if detected_type not in self.allowed_mime_types:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {detected_type}")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to determine file type")
        
        # Load and validate image
        try:
            image = Image.open(io.BytesIO(content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if image is too large
            if max(image.size) > self.max_dimension:
                image.thumbnail((self.max_dimension, self.max_dimension), Image.Resampling.LANCZOS)
            
            # Compute perceptual hashes
            hashes = self.compute_hashes(image)
            
            # Generate file hash for deduplication
            file_hash = hashlib.sha256(content).hexdigest()
            
            return {
                'image': image,
                'hashes': hashes,
                'file_hash': file_hash,
                'content_type': detected_type,
                'file_size': len(content),
                'image_size': image.size
            }
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
    
    def compute_hashes(self, image: Image.Image) -> dict:
        """Compute multiple perceptual hashes for comprehensive comparison."""
        hashes = {}
        
        # Average hash - fast but less accurate
        hashes['ahash'] = str(imagehash.average_hash(image, hash_size=self.hash_size))
        
        # Perceptual hash - more accurate but slower
        hashes['phash'] = str(imagehash.phash(image, hash_size=self.hash_size))
        
        # Difference hash - good balance of speed and accuracy
        hashes['dhash'] = str(imagehash.dhash(image, hash_size=self.hash_size))
        
        # Wavelet hash - good for scaled images
        hashes['whash'] = str(imagehash.whash(image, hash_size=self.hash_size))
        
        return hashes
    
    def calculate_similarity(self, hash1: str, hash2: str) -> int:
        """Calculate Hamming distance between two hashes."""
        if len(hash1) != len(hash2):
            return 64  # Maximum distance if lengths don't match
        
        # Convert hex strings to binary and calculate differences
        try:
            bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
            bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
            return sum(b1 != b2 for b1, b2 in zip(bin1, bin2))
        except ValueError:
            return 64  # Maximum distance if conversion fails

# Global image processor instance
image_processor = ImageProcessor()

# Pydantic Models
class ImageLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    url: str
    file_hash: str
    ahash: str
    phash: str
    dhash: str
    whash: str
    content_type: str
    file_size: int
    image_width: int
    image_height: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ImageLinkCreate(BaseModel):
    url: str

class ScanResult(BaseModel):
    matches_found: int
    best_match: Optional[dict] = None
    redirect_url: Optional[str] = None

# API Routes
@api_router.post("/link-image", response_model=dict)
async def link_image_to_url(
    url: str = Form(...),
    file: UploadFile = File(...)
):
    """Link an uploaded image to a URL."""
    try:
        # Process the image
        result = await image_processor.validate_and_process_image(file)
        
        # Check if this exact image already exists
        existing = await db.image_links.find_one({"file_hash": result['file_hash']})
        if existing:
            # Update the URL for existing image
            await db.image_links.update_one(
                {"file_hash": result['file_hash']},
                {"$set": {"url": url, "updated_at": datetime.utcnow()}}
            )
            return {
                "status": "updated",
                "message": f"Updated URL for existing image: {file.filename}",
                "image_id": existing['id'],
                "url": url
            }
        
        # Create new image link
        image_link = ImageLink(
            filename=file.filename or "unknown",
            url=url,
            file_hash=result['file_hash'],
            ahash=result['hashes']['ahash'],
            phash=result['hashes']['phash'],
            dhash=result['hashes']['dhash'],
            whash=result['hashes']['whash'],
            content_type=result['content_type'],
            file_size=result['file_size'],
            image_width=result['image_size'][0],
            image_height=result['image_size'][1]
        )
        
        # Store in database
        await db.image_links.insert_one(image_link.dict())
        
        return {
            "status": "created",
            "message": f"Successfully linked {file.filename} to {url}",
            "image_id": image_link.id,
            "url": url,
            "hashes": result['hashes']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.post("/scan-image", response_model=dict)
async def scan_image_for_url(
    file: UploadFile = File(...),
    threshold: int = Form(default=10)
):
    """Scan an image and find matching URLs."""
    try:
        # Process the uploaded image
        result = await image_processor.validate_and_process_image(file)
        query_hashes = result['hashes']
        
        # Search for similar images in database
        stored_images = await db.image_links.find({}).to_list(1000)
        
        best_match = None
        best_distance = float('inf')
        
        for stored_image in stored_images:
            # Calculate similarity using different algorithms
            distances = {}
            for algorithm in ['dhash', 'phash', 'ahash', 'whash']:
                if algorithm in query_hashes and algorithm in stored_image:
                    distance = image_processor.calculate_similarity(
                        query_hashes[algorithm], 
                        stored_image[algorithm]
                    )
                    distances[algorithm] = distance
            
            if distances:
                # Use the minimum distance (best match) from all algorithms
                min_distance = min(distances.values())
                
                if min_distance <= threshold and min_distance < best_distance:
                    best_distance = min_distance
                    best_match = {
                        'id': stored_image['id'],
                        'filename': stored_image['filename'],
                        'url': stored_image['url'],
                        'distance': min_distance,
                        'similarity_percentage': max(0, 100 - (min_distance * 10)),
                        'algorithm_used': min(distances, key=distances.get),
                        'created_at': stored_image['created_at']
                    }
        
        if best_match:
            return {
                "status": "match_found",
                "message": f"Found matching image: {best_match['filename']}",
                "match": best_match,
                "redirect_url": best_match['url'],
                "total_stored_images": len(stored_images)
            }
        else:
            return {
                "status": "no_match",
                "message": "No matching images found",
                "match": None,
                "redirect_url": None,
                "total_stored_images": len(stored_images),
                "threshold_used": threshold
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.get("/stored-images", response_model=dict)
async def get_stored_images():
    """Get list of all stored image links."""
    try:
        images = await db.image_links.find({}).to_list(1000)
        
        # Format response
        formatted_images = []
        for img in images:
            formatted_images.append({
                'id': img['id'],
                'filename': img['filename'],
                'url': img['url'],
                'content_type': img['content_type'],
                'file_size': img['file_size'],
                'image_size': f"{img['image_width']}x{img['image_height']}",
                'created_at': img['created_at']
            })
        
        return {
            "total_images": len(formatted_images),
            "images": formatted_images
        }
        
    except Exception as e:
        logger.error(f"Error retrieving stored images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.delete("/stored-images/{image_id}")
async def delete_stored_image(image_id: str):
    """Delete a stored image link."""
    try:
        result = await db.image_links.delete_one({"id": image_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Image not found")
        
        return {"message": "Image link deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Root route to serve the main page
@app.get("/", response_class=HTMLResponse)
async def serve_main_page():
    """Serve the main application page."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image-to-URL Recognition</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <h1>Image-to-URL Recognition App</h1>
        <p>This app allows you to link images to URLs and scan images to navigate to linked URLs.</p>
        <p>Use the React frontend for the full experience.</p>
        <a href="/api/docs">API Documentation</a>
    </body>
    </html>
    """

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()