"""
Cache system to make queries faster
Remembers similar questions so I don't have to process them again
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class QueryCache:
    """
    Saves query results so I can return them quickly next time
    
    What it does:
    - Checks if I've seen the exact same query before
    - Checks if I've seen a similar query before
    - Automatically removes old stuff when it gets full
    - Tracks how well the cache is working
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        similarity_threshold: float = 0.92,
        ttl_seconds: Optional[int] = 3600,
        enable_semantic_cache: bool = True
    ):
        """
        Set up my cache
        
        Args:
            max_size: How many queries to remember before I start forgetting old ones
            similarity_threshold: How similar queries need to be to count as the same (0.92 = 92% similar)
            ttl_seconds: How long to keep stuff before it expires (None = keep forever)
            enable_semantic_cache: Whether to check for similar questions (slower but smarter)
        """
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.enable_semantic_cache = enable_semantic_cache
        
        # Where I store exact matches
        self.exact_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Where I store similar queries
        self.semantic_cache: OrderedDict[str, Tuple[np.ndarray, Dict[str, Any], float, str]] = OrderedDict()
        
        # Keep track of how well my cache is working
        self.stats = {
            'exact_hits': 0,
            'semantic_hits': 0,
            'misses': 0,
            'total_queries': 0,
            'evictions': 0,
            'ttl_expirations': 0
        }
    
    def _generate_query_hash(self, query: str, k: int = 5) -> str:
        """Create a unique ID for this query"""
        # Clean it up first
        normalized = query.lower().strip()
        # Add the k parameter so same query with different k values are separate
        cache_key = f"{normalized}|k={k}"
        return hashlib.sha256(cache_key.encode()).hexdigest()
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if this cached entry is too old"""
        if self.ttl_seconds is None:
            return False
        return (time.time() - timestamp) > self.ttl_seconds
    
    def _evict_oldest(self, cache: OrderedDict):
        """Kick out the oldest thing in the cache"""
        if cache:
            cache.popitem(last=False)  # Remove oldest (FIFO)
            self.stats['evictions'] += 1
    
    def _ensure_cache_size(self):
        """Make sure I don't remember too much stuff"""
        total_entries = len(self.exact_cache) + len(self.semantic_cache)
        
        while total_entries > self.max_size:
            # Remove from whichever cache is bigger
            if len(self.exact_cache) >= len(self.semantic_cache):
                self._evict_oldest(self.exact_cache)
            else:
                self._evict_oldest(self.semantic_cache)
            total_entries -= 1
    
    def get(
        self, 
        query: str, 
        k: int = 5,
        query_embedding: Optional[np.ndarray] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Try to find a cached answer for this query
        
        Args:
            query: What the user is asking
            k: How many results they want
            query_embedding: The vector representation of the query (for finding similar ones)
        
        Returns:
            The cached answer if I found one, otherwise None
        """
        self.stats['total_queries'] += 1
        query_hash = self._generate_query_hash(query, k)
        
        # First, check if I've seen this exact query before
        if query_hash in self.exact_cache:
            entry = self.exact_cache[query_hash]
            
            # Make sure it hasn't expired
            if self._is_expired(entry['timestamp']):
                del self.exact_cache[query_hash]
                self.stats['ttl_expirations'] += 1
            else:
                # Mark it as recently used
                self.exact_cache.move_to_end(query_hash)
                self.stats['exact_hits'] += 1
                
                # Give them a copy so they can't mess with my cache
                return self._create_cache_response(entry['data'], 'exact')
        
        # Next, check if I've seen something similar
        if self.enable_semantic_cache and query_embedding is not None:
            best_match = None
            best_similarity = 0.0
            best_hash = None
            
            # Look through all my cached queries to find the most similar one
            for cached_hash, (cached_embedding, cached_data, timestamp, original_query) in self.semantic_cache.items():
                # Skip expired stuff
                if self._is_expired(timestamp):
                    continue
                
                # See how similar this query is to what I'm looking for
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    cached_embedding.reshape(1, -1)
                )[0][0]
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = cached_data
                    best_hash = cached_hash
            
            # If I found something similar enough, use it
            if best_similarity >= self.similarity_threshold:
                # Mark it as recently used
                self.semantic_cache.move_to_end(best_hash)
                self.stats['semantic_hits'] += 1
                
                return self._create_cache_response(best_match, 'semantic', best_similarity)
        
        # Didn't find anything cached
        self.stats['misses'] += 1
        return None
    
    def set(
        self,
        query: str,
        response_data: Dict[str, Any],
        k: int = 5,
        query_embedding: Optional[np.ndarray] = None
    ):
        """
        Save a query result to cache
        
        Args:
            query: What the user asked
            response_data: The answer I gave them
            k: How many results they wanted
            query_embedding: The vector representation (for similarity matching later)
        """
        query_hash = self._generate_query_hash(query, k)
        timestamp = time.time()
        
        # Save it in the exact match cache
        self.exact_cache[query_hash] = {
            'data': response_data,
            'timestamp': timestamp,
            'query': query
        }
        
        # Mark it as the most recent
        self.exact_cache.move_to_end(query_hash)
        
        # Also save in semantic cache if I have the embedding
        if self.enable_semantic_cache and query_embedding is not None:
            self.semantic_cache[query_hash] = (
                query_embedding,
                response_data,
                timestamp,
                query
            )
            self.semantic_cache.move_to_end(query_hash)
        
        # Make sure I don't go over my size limit
        self._ensure_cache_size()
    
    def _create_cache_response(
        self, 
        data: Dict[str, Any], 
        cache_type: str,
        similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """Add some info about where this came from"""
        response = data.copy()
        response['_cache_hit'] = True
        response['_cache_type'] = cache_type
        
        if similarity is not None:
            response['_cache_similarity'] = float(similarity)
        
        return response
    
    def clear(self):
        """Forget everything I've cached"""
        self.exact_cache.clear()
        self.semantic_cache.clear()
    
    def remove_expired(self):
        """Clean out stuff that's gotten too old"""
        if self.ttl_seconds is None:
            return
        
        current_time = time.time()
        
        # Clean exact cache
        expired_exact = [
            key for key, value in self.exact_cache.items()
            if (current_time - value['timestamp']) > self.ttl_seconds
        ]
        for key in expired_exact:
            del self.exact_cache[key]
            self.stats['ttl_expirations'] += 1
        
        # Clean semantic cache
        expired_semantic = [
            key for key, (_, _, timestamp, _) in self.semantic_cache.items()
            if (current_time - timestamp) > self.ttl_seconds
        ]
        for key in expired_semantic:
            del self.semantic_cache[key]
            self.stats['ttl_expirations'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """See how well my cache is doing"""
        total_hits = self.stats['exact_hits'] + self.stats['semantic_hits']
        hit_rate = (total_hits / self.stats['total_queries'] * 100) if self.stats['total_queries'] > 0 else 0
        
        return {
            **self.stats,
            'total_hits': total_hits,
            'hit_rate_percent': round(hit_rate, 2),
            'exact_cache_size': len(self.exact_cache),
            'semantic_cache_size': len(self.semantic_cache),
            'total_cache_size': len(self.exact_cache) + len(self.semantic_cache)
        }
    
    def reset_stats(self):
        """Start counting from zero again"""
        self.stats = {
            'exact_hits': 0,
            'semantic_hits': 0,
            'misses': 0,
            'total_queries': 0,
            'evictions': 0,
            'ttl_expirations': 0
        }


class ChunkCache:
    """
    Saves the actual text chunks so I don't have to search the database again
    """
    
    def __init__(self, max_size: int = 500, ttl_seconds: Optional[int] = 1800):
        """
        Set up chunk cache
        
        Args:
            max_size: How many sets of chunks to remember
            ttl_seconds: How long to keep them
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Where I store the chunks
        self.cache: OrderedDict[str, Tuple[List, float]] = OrderedDict()
        
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
    
    def _generate_embedding_hash(self, embedding: np.ndarray, k: int) -> str:
        """Make a unique ID for this embedding"""
        # Just use the first 100 numbers to keep it fast
        hash_input = np.concatenate([embedding[:100], [k]]).tobytes()
        return hashlib.sha256(hash_input).hexdigest()
    
    def get(self, embedding: np.ndarray, k: int) -> Optional[List]:
        """Try to find cached chunks for this search"""
        cache_key = self._generate_embedding_hash(embedding, k)
        
        if cache_key in self.cache:
            chunks, timestamp = self.cache[cache_key]
            
            # Make sure it's not expired
            if self.ttl_seconds and (time.time() - timestamp) > self.ttl_seconds:
                del self.cache[cache_key]
                self.stats['expirations'] += 1
                self.stats['misses'] += 1
                return None
            
            # Mark as recently used
            self.cache.move_to_end(cache_key)
            self.stats['hits'] += 1
            return chunks
        
        self.stats['misses'] += 1
        return None
    
    def set(self, embedding: np.ndarray, k: int, chunks: List):
        """Save these chunks for later"""
        cache_key = self._generate_embedding_hash(embedding, k)
        
        self.cache[cache_key] = (chunks, time.time())
        self.cache.move_to_end(cache_key)
        
        # Remove oldest stuff if I'm getting too full
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
            self.stats['evictions'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """See how well the chunk cache is working"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self.cache)
        }
