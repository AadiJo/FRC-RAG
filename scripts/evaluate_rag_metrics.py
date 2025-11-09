#!/usr/bin/env python3
"""
FRC RAG Pipeline Evaluation Script

This script evaluates the retrieval and image relevance performance of the FRC RAG system
using metrics discussed in retrieval evaluation literature:
- Hit Rate @ K
- Precision @ K 
- Recall @ K
- F1 @ K
- Image Relevance metrics

Usage:
    python scripts/evaluate_rag_metrics.py --k 15 --test-queries test_queries.json
"""

import sys
import os
import json
import argparse
import time
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.src.core.query_processor import QueryProcessor
from backend.src.server.config import get_config

class RAGEvaluator:
    """Evaluator for FRC RAG pipeline performance using retrieval metrics"""
    
    def __init__(self, query_processor: QueryProcessor):
        self.query_processor = query_processor
        self.results = {}
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        return " ".join(text.lower().split())
    
    def hit_rate_at_k(self, retrieved_docs: List[Dict], ground_truth_keywords: List[str], k: int) -> bool:
        """
        Hit Rate @ K: Binary indicator if at least one relevant doc exists in top k
        Returns True if retrieved docs contain relevant keywords from ground truth
        """
        for i, doc in enumerate(retrieved_docs[:k]):
            if i >= len(retrieved_docs):
                break
            doc_content = doc.get('page_content', '') or doc.get('content', '')
            doc_norm = self.normalize_text(doc_content)
            
            # Count keyword matches in this document
            keyword_matches = 0
            for keyword in ground_truth_keywords:
                if keyword.lower() in doc_norm:
                    keyword_matches += 1
            
            # Document is relevant if it contains at least 20% of keywords
            relevance_threshold = max(1, len(ground_truth_keywords) * 0.2)
            if keyword_matches >= relevance_threshold:
                return True
                
        return False
    
    def precision_at_k(self, retrieved_docs: List[Dict], ground_truth_keywords: List[str], k: int) -> float:
        """
        Precision @ K: Proportion of retrieved docs that are relevant
        """
        if k == 0:
            return 0.0
            
        relevant_docs = 0
        for i, doc in enumerate(retrieved_docs[:k]):
            if i >= len(retrieved_docs):
                break
            doc_content = doc.get('page_content', '') or doc.get('content', '')
            doc_norm = self.normalize_text(doc_content)
            
            # Count keyword matches in this document
            keyword_matches = 0
            for keyword in ground_truth_keywords:
                if keyword.lower() in doc_norm:
                    keyword_matches += 1
            
            # Document is relevant if it contains at least 20% of keywords
            relevance_threshold = max(1, len(ground_truth_keywords) * 0.2)
            if keyword_matches >= relevance_threshold:
                relevant_docs += 1
                    
        return relevant_docs / k
    
    def recall_at_k(self, retrieved_docs: List[Dict], ground_truth_keywords: List[str], k: int) -> float:
        """
        Recall @ K: Proportion of ground truth concepts found in retrieved docs
        """
        if not ground_truth_keywords:
            return 0.0
        
        # Combine all retrieved document content
        all_retrieved_text = ""
        for i, doc in enumerate(retrieved_docs[:k]):
            if i >= len(retrieved_docs):
                break
            doc_content = doc.get('page_content', '') or doc.get('content', '')
            all_retrieved_text += " " + doc_content
        
        all_retrieved_norm = self.normalize_text(all_retrieved_text)
        
        # Count how many keywords are found in the retrieved content
        found_keywords = 0
        for keyword in ground_truth_keywords:
            if keyword.lower() in all_retrieved_norm:
                found_keywords += 1
                    
        return found_keywords / len(ground_truth_keywords)
    
    def f1_at_k(self, precision: float, recall: float) -> float:
        """
        F1 @ K: Harmonic mean of precision and recall
        """
        return 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    def _calculate_overlap_percentage(self, text1: str, text2: str) -> float:
        """Calculate percentage of word overlap between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
            
        overlap = len(words1.intersection(words2))
        total_unique = len(words1.union(words2))
        
        return overlap / total_unique if total_unique > 0 else 0.0
    
    def evaluate_image_relevance(self, images: List[Dict], query: str, expected_keywords: List[str]) -> Dict[str, float]:
        """
        Evaluate image relevance based on OCR content and context
        """
        if not images:
            return {
                'image_count': 0,
                'relevant_images': 0,
                'image_relevance_rate': 0.0,
                'avg_context_relevance': 0.0
            }
        
        relevant_count = 0
        context_scores = []
        
        for img in images:
            ocr_text = img.get('ocr_text', '').lower()
            context_text = img.get('context_summary', '').lower()
            filename = img.get('filename', '').lower()
            
            # Check for keyword matches in various fields
            relevance_score = 0
            total_checks = len(expected_keywords)
            
            for keyword in expected_keywords:
                keyword = keyword.lower()
                if (keyword in ocr_text or 
                    keyword in context_text or 
                    keyword in filename):
                    relevance_score += 1
            
            # Image is relevant if it matches at least 1 keyword
            if relevance_score > 0:
                relevant_count += 1
            
            # Calculate context relevance (0-1 scale)
            context_relevance = relevance_score / total_checks if total_checks > 0 else 0
            context_scores.append(context_relevance)
        
        return {
            'image_count': len(images),
            'relevant_images': relevant_count,
            'image_relevance_rate': relevant_count / len(images),
            'avg_context_relevance': np.mean(context_scores) if context_scores else 0.0
        }
    
    def evaluate_single_query(self, query: str, ground_truth: Dict[str, Any], k: int = 15) -> Dict[str, Any]:
        """
        Evaluate a single query against ground truth
        
        Args:
            query: The query string
            ground_truth: Dict containing 'relevant_chunks' and 'expected_keywords'
            k: Number of top results to evaluate
            
        Returns:
            Dict with evaluation metrics
        """
        start_time = time.time()
        
        # Get query results
        result = self.query_processor.process_query(query, k)
        
        retrieval_time = time.time() - start_time
        
        if "error" in result:
            return {
                'query': query,
                'error': result["error"],
                'retrieval_time': retrieval_time
            }
        
        # Extract document results for evaluation
        # Try multiple ways to get the retrieved documents
        retrieved_docs = []
        
        # Method 1: Try to get from context_parts (most likely)
        if 'context_parts' in result and result['context_parts']:
            for i, content in enumerate(result['context_parts']):
                retrieved_docs.append({
                    'page_content': content,
                    'rank': i
                })
        
        # Method 2: Try to get from a direct response field
        elif 'documents' in result:
            retrieved_docs = result['documents']
        
        # Method 3: If we still don't have docs, try to extract from response text
        elif 'response' in result and result['response']:
            # This is a fallback - treat the response as a single document
            retrieved_docs = [{
                'page_content': result['response'],
                'rank': 0
            }]
        
        print(f"    Retrieved {len(retrieved_docs)} documents for evaluation")
        
        # Get ground truth data
        ground_truth_texts = ground_truth.get('relevant_chunks', [])
        expected_keywords = ground_truth.get('expected_keywords', [])
        
        # Use keywords for evaluation (more reliable than exact text matching)
        evaluation_keywords = expected_keywords if expected_keywords else []
        
        # Calculate retrieval metrics using keywords
        hit_rate = self.hit_rate_at_k(retrieved_docs, evaluation_keywords, k)
        precision = self.precision_at_k(retrieved_docs, evaluation_keywords, k)
        recall = self.recall_at_k(retrieved_docs, evaluation_keywords, k)
        f1_score = self.f1_at_k(precision, recall)
        
        # Debug information
        debug_info = {
            'total_keywords': len(evaluation_keywords),
            'keywords_sample': evaluation_keywords[:5] if evaluation_keywords else [],
            'retrieved_docs_sample': [doc.get('page_content', '')[:100] + '...' 
                                    if len(doc.get('page_content', '')) > 100 
                                    else doc.get('page_content', '') 
                                    for doc in retrieved_docs[:2]]
        }
        
        # Calculate image metrics
        images = result.get('related_images', [])
        image_metrics = self.evaluate_image_relevance(images, query, expected_keywords)
        
        return {
            'query': query,
            'k': k,
            'retrieval_time': retrieval_time,
            'hit_rate_at_k': hit_rate,
            'precision_at_k': precision,
            'recall_at_k': recall,
            'f1_at_k': f1_score,
            'documents_retrieved': len(retrieved_docs),
            'context_sources': result.get('context_sources', 0),
            'debug_info': debug_info,
            **image_metrics,
            'enhanced_query': result.get('enhanced_query', query),
            'matched_pieces': result.get('matched_pieces', [])
        }
    
    def evaluate_test_set(self, test_queries: Dict[str, Dict], k_values: List[int] = None) -> Dict[str, Any]:
        """
        Evaluate multiple queries and calculate average metrics
        
        Args:
            test_queries: Dict mapping query strings to ground truth data
            k_values: List of k values to evaluate (default: [5, 10, 15, 20])
            
        Returns:
            Comprehensive evaluation results
        """
        if k_values is None:
            k_values = [5, 10, 15, 20]
        
        results = {
            'individual_results': {},
            'aggregate_metrics': {},
            'k_values': k_values,
            'total_queries': len(test_queries)
        }
        
        for k in k_values:
            print(f"\nEvaluating with k={k}...")
            
            query_results = []
            
            for query, ground_truth in test_queries.items():
                print(f"  Evaluating: {query[:60]}...")
                
                query_result = self.evaluate_single_query(query, ground_truth, k)
                query_results.append(query_result)
                
                # Store individual result
                if query not in results['individual_results']:
                    results['individual_results'][query] = {}
                results['individual_results'][query][f'k_{k}'] = query_result
            
            # Calculate aggregate metrics for this k
            valid_results = [r for r in query_results if 'error' not in r]
            
            if valid_results:
                aggregate = {
                    'avg_hit_rate': np.mean([r['hit_rate_at_k'] for r in valid_results]),
                    'avg_precision': np.mean([r['precision_at_k'] for r in valid_results]),
                    'avg_recall': np.mean([r['recall_at_k'] for r in valid_results]),
                    'avg_f1': np.mean([r['f1_at_k'] for r in valid_results]),
                    'avg_retrieval_time': np.mean([r['retrieval_time'] for r in valid_results]),
                    'avg_documents_retrieved': np.mean([r['documents_retrieved'] for r in valid_results]),
                    'avg_image_count': np.mean([r['image_count'] for r in valid_results]),
                    'avg_relevant_images': np.mean([r['relevant_images'] for r in valid_results]),
                    'avg_image_relevance_rate': np.mean([r['image_relevance_rate'] for r in valid_results]),
                    'avg_context_relevance': np.mean([r['avg_context_relevance'] for r in valid_results]),
                    'successful_queries': len(valid_results),
                    'failed_queries': len(query_results) - len(valid_results)
                }
                
                results['aggregate_metrics'][f'k_{k}'] = aggregate
                
                # Print summary for this k
                print(f"    Hit Rate@{k}: {aggregate['avg_hit_rate']:.3f}")
                print(f"    Precision@{k}: {aggregate['avg_precision']:.3f}")
                print(f"    Recall@{k}: {aggregate['avg_recall']:.3f}")
                print(f"    F1@{k}: {aggregate['avg_f1']:.3f}")
                print(f"    Avg Images: {aggregate['avg_image_count']:.1f}")
                print(f"    Image Relevance: {aggregate['avg_image_relevance_rate']:.3f}")
                print(f"    Avg Time: {aggregate['avg_retrieval_time']:.2f}s")
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """Save evaluation results to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
    
    def print_summary_report(self, results: Dict[str, Any]):
        """Print a formatted summary report"""
        print("\n" + "="*70)
        print("FRC RAG EVALUATION SUMMARY REPORT")
        print("="*70)
        
        total_queries = results['total_queries']
        k_values = results['k_values']
        
        print(f"\nTest Set: {total_queries} queries evaluated")
        print(f"K values tested: {k_values}")
        
        print(f"\n{'Metric':<25} " + " ".join([f"k={k:<4}" for k in k_values]))
        print("-" * 70)
        
        metrics = ['avg_hit_rate', 'avg_precision', 'avg_recall', 'avg_f1', 
                  'avg_image_relevance_rate', 'avg_retrieval_time']
        metric_names = ['Hit Rate', 'Precision', 'Recall', 'F1 Score', 
                       'Image Relevance', 'Response Time (s)']
        
        for metric, name in zip(metrics, metric_names):
            row = f"{name:<25}"
            for k in k_values:
                k_key = f'k_{k}'
                if k_key in results['aggregate_metrics']:
                    value = results['aggregate_metrics'][k_key][metric]
                    if metric == 'avg_retrieval_time':
                        row += f" {value:>6.2f}"
                    else:
                        row += f" {value:>6.3f}"
                else:
                    row += f" {'N/A':>6}"
            print(row)
        
        # Find best performing k
        best_k = None
        best_f1 = 0
        for k in k_values:
            k_key = f'k_{k}'
            if k_key in results['aggregate_metrics']:
                f1 = results['aggregate_metrics'][k_key]['avg_f1']
                if f1 > best_f1:
                    best_f1 = f1
                    best_k = k
        
        if best_k:
            print(f"\nBest performing configuration: k={best_k} (F1: {best_f1:.3f})")
        
        print("\n" + "="*70)

def load_test_queries(file_path: str) -> Dict[str, Dict]:
    """Load test queries from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Test queries file not found: {file_path}")
        return create_default_test_queries()

def create_default_test_queries() -> Dict[str, Dict]:
    """Create default test queries for FRC RAG evaluation"""
    return {
        "Design a versatile intake mechanism for the 2024 CRESCENDO season that can handle Note game pieces. The intake must be able to pick up Notes from the ground, accept handoffs from human players at the Source, and work reliably in autonomous mode. Include specific constraints for robot dimensions, motor specifications, and material choices.": {
            "relevant_chunks": [
                "intake mechanism design for Note game pieces",
                "ground pickup system for foam rings",
                "human player handoff interface",
                "autonomous intake operation"
            ],
            "expected_keywords": [
                "intake", "note", "roller", "belt", "motor", "neo", "ground", 
                "source", "autonomous", "sensor", "beam break", "foam ring"
            ]
        },
        "How do you design a drivetrain for a 120lb robot that can achieve 15 ft/s top speed using maximum 4 CIM motors?": {
            "relevant_chunks": [
                "drivetrain design calculations",
                "CIM motor specifications",
                "gear ratio calculations for speed",
                "weight considerations for drivetrain"
            ],
            "expected_keywords": [
                "drivetrain", "CIM", "motor", "gear", "ratio", "speed", "weight", 
                "wheels", "gearbox", "transmission", "fps", "ft/s"
            ]
        },
        "What sensors are commonly used in FRC robots for autonomous navigation?": {
            "relevant_chunks": [
                "autonomous navigation sensor systems",
                "gyroscope and IMU usage",
                "encoder feedback systems",
                "vision and camera integration"
            ],
            "expected_keywords": [
                "sensor", "autonomous", "navigation", "gyro", "encoder", "IMU", 
                "camera", "vision", "ultrasonic", "lidar", "apriltag"
            ]
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Evaluate FRC RAG Pipeline Performance')
    parser.add_argument('--k', type=int, nargs='+', default=[5, 10, 15, 20],
                       help='K values to evaluate (default: 5 10 15 20)')
    parser.add_argument('--test-queries', type=str, default='test_queries.json',
                       help='Path to test queries JSON file')
    parser.add_argument('--output', type=str, default='evaluation_results.json',
                       help='Output file for results')
    parser.add_argument('--config', type=str, help='Path to config file')
    
    args = parser.parse_args()
    
    print("Starting FRC RAG Pipeline Evaluation...")
    
    # Initialize system
    try:
        Config = get_config()
        query_processor = QueryProcessor(Config.CHROMA_PATH, Config.IMAGES_PATH)
        print("Query processor initialized successfully")
    except Exception as e:
        print(f"Error initializing query processor: {e}")
        return 1
    
    # Load test queries
    test_queries = load_test_queries(args.test_queries)
    print(f"Loaded {len(test_queries)} test queries")
    
    # Initialize evaluator
    evaluator = RAGEvaluator(query_processor)
    
    # Run evaluation
    print(f"Evaluating with k values: {args.k}")
    results = evaluator.evaluate_test_set(test_queries, args.k)
    
    # Print summary
    evaluator.print_summary_report(results)
    
    # Save results
    evaluator.save_results(results, args.output)
    
    print("\nEvaluation completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())