import os
import shutil
import glob
import json
from typing import List, Dict, Any
import fitz  # PyMuPDF
from PIL import Image
import io
import hashlib
import base64

from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import pytesseract

# Configure paths
DATA_PATH = "data"
IMAGES_PATH = os.path.join(DATA_PATH, "images")
CHROMA_PATH = "db"

# Image filtering settings
MIN_IMAGE_SIZE = (80, 80)  # Minimum width and height
MAX_ASPECT_RATIO = 20  # Filter out extremely wide/tall images
MIN_OCR_CHARS = 3  # Minimum OCR characters to consider image useful
MIN_FILE_SIZE = 1000  # Minimum file size in bytes

def main():
    print("Starting database creation...")
    
    # Clear existing database
    if os.path.exists(CHROMA_PATH):
        print(f"Removing existing database at {CHROMA_PATH}")
        shutil.rmtree(CHROMA_PATH)
    
    # Find all PDF files in the data directory
    pdf_files = glob.glob(os.path.join(DATA_PATH, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {DATA_PATH}")
        return
    
    print(f"Found {len(pdf_files)} PDF files: {[os.path.basename(f) for f in pdf_files]}")
    
    all_documents = []
    
    # Process each PDF file
    for pdf_path in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {os.path.basename(pdf_path)}")
        print(f"{'='*60}")
        
        # Create PDF-specific image folder
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_images_path = os.path.join(IMAGES_PATH, pdf_name)
        
        # Clear existing images for this PDF
        if os.path.exists(pdf_images_path):
            print(f"Removing existing images at {pdf_images_path}")
            shutil.rmtree(pdf_images_path)
        
        # Ensure directories exist
        os.makedirs(pdf_images_path, exist_ok=True)
        
        # Process this PDF
        try:
            documents = process_pdf_with_images(pdf_path, pdf_images_path)
            all_documents.extend(documents)
            print(f"Successfully processed {os.path.basename(pdf_path)}: {len(documents)} documents")
        except Exception as e:
            print(f"Error processing {os.path.basename(pdf_path)}: {e}")
            continue
    
    if not all_documents:
        print("No documents were successfully processed.")
        return
    
    print(f"\n{'='*60}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total documents created: {len(all_documents)}")
    
    # Split text into chunks
    chunks = split_text(all_documents)
    
    # Save to vector database
    save_to_chroma(chunks)
    
    print("Enhanced database creation completed!")

def process_pdf_with_images(pdf_path: str, pdf_images_path: str) -> List[Document]:
    """
    Process PDF to extract both text and images, linking them together
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")
    
    documents = []
    
    # Open PDF
    pdf_document = fitz.open(pdf_path)
    print(f"Processing PDF with {len(pdf_document)} pages...")
    
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        # Extract text from page
        page_text = page.get_text()
        
        if page_text.strip():  # Only process pages with text
            # Extract images from this page
            image_info = extract_images_from_page(page, page_num, pdf_images_path)
            
            # Create document with text and image references
            metadata = {
                "source": pdf_path,
                "page": page_num + 1,  # 1-indexed for user friendliness
                "type": "text_with_images",
                "image_count": len(image_info),
                "image_filenames": json.dumps([img["filename"] for img in image_info]) if image_info else "[]"
            }
            
            # Add image descriptions to the text content if images exist
            enhanced_content = page_text
            if image_info:
                image_descriptions = []
                for img_info in image_info:
                    if img_info.get("ocr_text"):
                        image_descriptions.append(f"[Image {img_info['filename']}: {img_info['ocr_text']}]")
                    else:
                        image_descriptions.append(f"[Image {img_info['filename']}: Visual content on page {page_num + 1}]")
                
                enhanced_content += "\n\nImages on this page:\n" + "\n".join(image_descriptions)
            
            document = Document(
                page_content=enhanced_content,
                metadata=metadata
            )
            documents.append(document)
            
            # Store image info separately for later retrieval
            if image_info:
                for img_info in image_info:
                    # Create a simple metadata entry for image info
                    img_metadata = {
                        "source": pdf_path,
                        "page": page_num + 1,
                        "type": "image_info",
                        "image_file": img_info["filename"],
                        "image_path": img_info["file_path"],
                        "has_ocr_text": bool(img_info.get("ocr_text", "").strip())
                    }
                    
                    # Create a document just for storing image metadata
                    img_doc = Document(
                        page_content=f"Image metadata for {img_info['filename']} on page {page_num + 1}",
                        metadata=img_metadata
                    )
                    documents.append(img_doc)
            
            # Create separate documents for each image with OCR text
            for img_info in image_info:
                if img_info.get("ocr_text") and img_info["ocr_text"].strip():
                    img_document = Document(
                        page_content=f"Image content: {img_info['ocr_text']}\n\nContext: This image appears on page {page_num + 1} of the document.",
                        metadata={
                            "source": pdf_path,
                            "page": page_num + 1,
                            "type": "image_text",
                            "image_file": img_info["filename"],
                            "image_path": img_info["file_path"]
                        }
                    )
                    documents.append(img_document)
    
    total_pages = len(pdf_document)
    pdf_document.close()
    print(f"Extracted content from {total_pages} pages, created {len(documents)} documents")
    return documents

def extract_images_from_page(page, page_num: int, pdf_images_path: str) -> List[Dict[str, Any]]:
    """
    Extract images from a specific PDF page with filtering
    """
    image_info = []
    image_list = page.get_images()
    
    for img_index, img in enumerate(image_list):
        try:
            # Get image data
            xref = img[0]
            pix = fitz.Pixmap(page.parent, xref)
            
            # Convert to PIL Image for processing
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_data = pix.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                
                # Filter out useless images
                if not is_useful_image(pil_image):
                    print(f"Filtered out image: page{page_num}_img{img_index}.png (not useful)")
                    pix = None
                    continue
                
                # Generate filename
                filename = f"page{page_num}_img{img_index}.png"
                file_path = os.path.join(pdf_images_path, filename)
                
                # Save image
                pil_image.save(file_path)
                
                # Check file size after saving
                if os.path.getsize(file_path) < MIN_FILE_SIZE:
                    print(f"Filtered out image: {filename} (too small file size)")
                    os.remove(file_path)
                    pix = None
                    continue
                
                # Perform OCR on the image
                ocr_text = ""
                try:
                    ocr_text = pytesseract.image_to_string(pil_image).strip()
                except Exception as e:
                    print(f"OCR failed for {filename}: {e}")
                
                # Filter based on OCR content
                if len(ocr_text) < MIN_OCR_CHARS and not has_meaningful_content(pil_image):
                    print(f"Filtered out image: {filename} (no meaningful content)")
                    os.remove(file_path)
                    pix = None
                    continue
                
                # Create image info
                img_info = {
                    "filename": filename,
                    "file_path": file_path,
                    "page": page_num + 1,
                    "index": img_index,
                    "ocr_text": ocr_text,
                    "size": pil_image.size
                }
                
                image_info.append(img_info)
                print(f"Extracted image: {filename} (OCR: {len(ocr_text)} chars, Size: {pil_image.size})")
            
            pix = None  # Free memory
            
        except Exception as e:
            print(f"Error extracting image {img_index} from page {page_num}: {e}")
    
    return image_info

def is_useful_image(pil_image: Image.Image) -> bool:
    """
    Filter out useless images based on size and aspect ratio
    """
    width, height = pil_image.size
    
    # Filter by minimum size
    if width < MIN_IMAGE_SIZE[0] or height < MIN_IMAGE_SIZE[1]:
        return False
    
    # Filter by aspect ratio (avoid extremely wide or tall images)
    aspect_ratio = max(width, height) / min(width, height)
    if aspect_ratio > MAX_ASPECT_RATIO:
        return False
    
    return True

def has_meaningful_content(pil_image: Image.Image) -> bool:
    """
    Check if image has meaningful visual content beyond simple shapes/logos
    """
    import numpy as np
    
    # Convert to numpy array for analysis
    img_array = np.array(pil_image.convert('L'))  # Convert to grayscale
    
    # Calculate variance - low variance suggests solid colors or simple content
    variance = np.var(img_array)
    
    # Calculate edge detection using simple gradient
    grad_x = np.gradient(img_array, axis=1)
    grad_y = np.gradient(img_array, axis=0)
    edge_magnitude = np.sqrt(grad_x**2 + grad_y**2)
    edge_density = np.mean(edge_magnitude > 10)  # Threshold for edge detection
    
    # Consider image meaningful if it has sufficient variance and edge content
    # These thresholds may need adjustment based on your specific images
    min_variance = 100  # Minimum pixel variance
    min_edge_density = 0.02  # Minimum proportion of edge pixels
    
    return variance > min_variance or edge_density > min_edge_density

def split_text(documents: List[Document]) -> List[Document]:
    """
    Split documents into chunks for better retrieval
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Larger chunks to maintain context
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    
    # Show sample chunk
    if chunks:
        print("\nSample chunk:")
        print(f"Content: {chunks[10].page_content[:200]}...")
        print(f"Metadata: {chunks[10].metadata}")
    
    return chunks

def save_to_chroma(chunks: List[Document]):
    """
    Save chunks to Chroma vector database
    """
    # Clear existing database
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    
    # Filter complex metadata manually
    filtered_chunks = []
    for chunk in chunks:
        # Create a new document with simple metadata
        simple_metadata = {}
        for key, value in chunk.metadata.items():
            # Only keep simple types that ChromaDB can handle
            if isinstance(value, (str, int, float, bool)):
                simple_metadata[key] = value
            elif isinstance(value, list):
                # Convert lists to strings
                simple_metadata[key] = str(value)
            else:
                # Convert other types to strings
                simple_metadata[key] = str(value)
        
        filtered_chunk = Document(
            page_content=chunk.page_content,
            metadata=simple_metadata
        )
        filtered_chunks.append(filtered_chunk)
    
    # Create embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    # Create and save database
    db = Chroma.from_documents(
        filtered_chunks, 
        embeddings, 
        persist_directory=CHROMA_PATH
    )
    
    print(f"Saved {len(filtered_chunks)} chunks to {CHROMA_PATH}")

def test_database():
    """
    Test the created database with sample queries
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    
    # Test query
    test_queries = [
        "tube shaped object",
        "coral picker",
        "CAD design",
        "gripper mechanism"
    ]
    
    print("\n" + "="*50)
    print("Testing database with sample queries:")
    print("="*50)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = db.similarity_search(query, k=3)
        
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Content: {result.page_content[:200]}...")
            print(f"Page: {result.metadata.get('page', 'N/A')}")
            print(f"Type: {result.metadata.get('type', 'N/A')}")
            if 'images' in result.metadata and result.metadata['images']:
                print(f"Associated images: {[img['filename'] for img in result.metadata['images']]}")
            if result.metadata.get('image_file'):
                print(f"Image file: {result.metadata['image_file']}")

if __name__ == "__main__":
    main()
    
    # Optionally test the database
    print("\nWould you like to test the database? (y/n)")
    if input().lower().startswith('y'):
        test_database()
