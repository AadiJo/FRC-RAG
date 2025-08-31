import argparse
import os
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.llms import Ollama

CHROMA_PATH = "chroma_enhanced"
IMAGES_PATH = "data/images"

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}

If relevant images are mentioned in the context, include references to them in your answer.
Based on the context and your knowledge, provide a detailed and accurate response, and draw conclusions if applicable.
If the context does not provide enough information for the full answer, connect what is provided with your own knowledge to give a comprehensive response.
"""

def main():
    # Create CLI
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--k", type=int, default=5, help="Number of results to retrieve")
    parser.add_argument("--show-images", action="store_true", help="Display image paths for relevant results")
    args = parser.parse_args()
    
    query_text = args.query_text
    k = args.k
    show_images = args.show_images

    # Prepare db
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    if not os.path.exists(CHROMA_PATH):
        print(f"Database not found at {CHROMA_PATH}. Please run create_database2.py first.")
        return
    
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search db
    results = db.similarity_search_with_relevance_scores(query_text, k=k)
    
    if len(results) == 0 or results[0][1] < 0.1:
        print(f"Unable to find matching results for: '{query_text}'")
        return

    # Process results and collect related images
    context_parts = []
    related_images = []
    
    print(f"\nFound {len(results)} relevant results:")
    print("=" * 60)
    
    for i, (doc, score) in enumerate(results, 1):
        print(f"\nResult {i} (Score: {score:.3f}):")
        print(f"Page: {doc.metadata.get('page', 'N/A')}")
        print(f"Type: {doc.metadata.get('type', 'N/A')}")
        print(f"Content: {doc.page_content[:200]}...")
        
        # Add to context
        context_parts.append(f"[Result {i} from page {doc.metadata.get('page', 'N/A')}]:\n{doc.page_content}")
        
        # Collect images
        images_info = collect_images_from_result(doc, show_images)
        if images_info:
            related_images.extend(images_info)
            if show_images:
                print(f"Associated images: {[img['filename'] for img in images_info]}")
    
    # Generate response using ollama
    context_text = "\n\n---\n\n".join(context_parts)
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    print("\n" + "=" * 60)
    print("Generating AI Response...")
    print("=" * 60)
    
    try:
        model = Ollama(model="mistral")
        response_text = model.invoke(prompt)
        
        print(f"\nAI Response:")
        print("-" * 40)
        print(response_text)
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        print("Showing context without AI processing...")
        print(f"\nDirect Context for '{query_text}':")
        print("-" * 40)
        response_text = context_text[:1000] + "..." if len(context_text) > 1000 else context_text
    
    # Collect unique images for output
    unique_images = {}
    for img in related_images:
        if img['filename'] not in unique_images:
            unique_images[img['filename']] = img
    
    # Clear terminal and display final clean summary
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("QUERY RESULTS")
    print("=" * 80)
    
    # Display Question
    print(f"\nQUESTION:")
    print(f"   {query_text}")
    
    # Display Answer
    print(f"\nANSWER:")
    print("-" * 50)
    print(response_text)
    
    # Display Related Images
    if unique_images:
        print(f"\nRELATED IMAGES:")
        print("-" * 50)
        
        for i, img_info in enumerate(unique_images.values(), 1):
            status_icon = "✅" if os.path.exists(img_info['file_path']) else "❌"
            print(f"\n{i}. {img_info['filename']} {status_icon}")
            print(f"   Path: {img_info['file_path']}")
            print(f"   Page: {img_info.get('page', 'N/A')}")
            
            if img_info.get('ocr_text') and img_info['ocr_text'].strip():
                # Clean up OCR text for display
                ocr_preview = img_info['ocr_text'].replace('\n', ' ').strip()
                if len(ocr_preview) > 100:
                    ocr_preview = ocr_preview[:97] + "..."
                print(f"   Content: {ocr_preview}")
    else:
        print(f"\nRELATED IMAGES:")
        print("-" * 50)
        print("   No images found related to this query.")
    
    # Final summary stats
    print(f"\nSUMMARY:")
    print("-" * 50)
    print(f"   • Query processed: {query_text}")
    print(f"   • Results found: {len(results)}")
    print(f"   • Images found: {len(unique_images)}")
    print(f"   • Database: {CHROMA_PATH}")
    print("\n" + "=" * 80)

def collect_images_from_result(doc, show_details=False) -> List[Dict[str, Any]]:
    """
    Collect image information from a document result
    """
    images_info = []
    
    # Check if this is an image document
    if doc.metadata.get('type') == 'image_text':
        image_file = doc.metadata.get('image_file')
        image_path = doc.metadata.get('image_path')
        if image_file and image_path:
            images_info.append({
                'filename': image_file,
                'file_path': image_path,
                'page': doc.metadata.get('page'),
                'ocr_text': doc.page_content.replace('Image content: ', '').split('\n\nContext:')[0]
            })
    
    # Check if this is an image metadata document
    elif doc.metadata.get('type') == 'image_info':
        image_file = doc.metadata.get('image_file')
        image_path = doc.metadata.get('image_path')
        if image_file and image_path:
            images_info.append({
                'filename': image_file,
                'file_path': image_path,
                'page': doc.metadata.get('page'),
                'ocr_text': ''
            })
    
    # Check if this document has associated images
    elif doc.metadata.get('type') == 'text_with_images':
        image_filenames_str = doc.metadata.get('image_filenames', '[]')
        try:
            import json
            image_filenames = json.loads(image_filenames_str)
            page_num = doc.metadata.get('page', 1)
            
            # Determine PDF name from source path
            source_path = doc.metadata.get('source', '')
            pdf_name = os.path.splitext(os.path.basename(source_path))[0] if source_path else ''
            
            for filename in image_filenames:
                # Construct path using PDF subfolder
                if pdf_name:
                    pdf_subfolder_path = os.path.join(IMAGES_PATH, pdf_name, filename)
                else:
                    pdf_subfolder_path = None
                
                legacy_path = os.path.join(IMAGES_PATH, filename)
                
                # Check both new and old paths for compatibility
                if pdf_subfolder_path and os.path.exists(pdf_subfolder_path):
                    file_path = pdf_subfolder_path
                elif os.path.exists(legacy_path):
                    file_path = legacy_path
                else:
                    file_path = pdf_subfolder_path if pdf_subfolder_path else legacy_path  # Use new path as default
                
                images_info.append({
                    'filename': filename,
                    'file_path': file_path,
                    'page': page_num,
                    'ocr_text': ''
                })
        except:
            pass  # If JSON parsing fails, continue without images
    
    return images_info

def interactive_mode():
    """
    Interactive query mode for testing
    """
    print("FRC RAG Database Query Tool")
    print("Enter 'quit' or 'exit' to stop")
    print("=" * 50)
    
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    if not os.path.exists(CHROMA_PATH):
        print(f"Database not found at {CHROMA_PATH}. Please run create_database2.py first.")
        return
    
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    
    while True:
        query = input("\nEnter your query: ").strip()
        
        if query.lower() in ['quit', 'exit', '']:
            break
            
        print(f"\nSearching for: '{query}'")
        
        # Simple search without ollama
        results = db.similarity_search_with_relevance_scores(query, k=3)
        
        if not results or results[0][1] < 0.1:
            print("No relevant results found.")
            continue
        
        print(f"\nTop {len(results)} results:")
        for i, (doc, score) in enumerate(results, 1):
            print(f"\n{i}. Score: {score:.3f} | Page: {doc.metadata.get('page', 'N/A')}")
            print(f"   {doc.page_content[:150]}...")
            
            # Show images
            images = collect_images_from_result(doc)
            if images:
                print(f"   Images: {[img['filename'] for img in images]}")

if __name__ == "__main__":
    if len(os.sys.argv) == 1:
        # No arguments provided, run in interactive mode
        interactive_mode()
    else:
        main()
