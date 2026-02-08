"""
Summarization module for reducing token consumption when processing search results.

This module provides functions to condense search results from TavilySearchResults
into a more compact format suitable for passing to LLMs using BERT-based models.
"""

import logging
import os
from transformers import pipeline
import torch
import re

logger = logging.getLogger("agent.summarization")

# Optional imports for BERT extractive summarization
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

try:
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    import numpy as np  # numpy is usually available
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")

logger = logging.getLogger("agent.summarization")

# Initialize summarization pipeline with BERT-based model
_summarizer = None
_bert_model = None
# Use a BERT-based model for summarization
# Options: 
# - "bert-base-uncased" for extractive summarization using embeddings
# - "facebook/bart-large-cnn" for abstractive summarization (BART uses BERT architecture)
# - "google/pegasus-xsum" for abstractive summarization
_model_name = os.getenv("SUMMARIZATION_MODEL", "facebook/bart-large-cnn")


def _get_summarizer():
    """Lazy initialization of the summarization pipeline."""
    global _summarizer
    if _summarizer is None:
        try:
            logger.info(f"Loading summarization model: {_model_name}")
            
            # Use CPU if CUDA not available
            device = 0 if torch.cuda.is_available() else -1
            
            _summarizer = pipeline(
                "summarization",
                model=_model_name,
                tokenizer=_model_name,
                device=device,
                max_length=150,  # Maximum length of summary
                min_length=30,   # Minimum length of summary
            )
            logger.info("Summarization model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load summarization model: {e}. Falling back to simple truncation.")
            _summarizer = None
    return _summarizer


def _get_bert_model():
    """Lazy initialization of BERT model for extractive summarization."""
    global _bert_model
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    if _bert_model is None:
        try:
            bert_model_name = os.getenv("BERT_MODEL", "bert-base-uncased")
            logger.info(f"Loading BERT model for extractive summarization: {bert_model_name}")
            _bert_model = SentenceTransformer(bert_model_name)
            logger.info("BERT model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load BERT model: {e}. Will use abstractive summarization.")
            _bert_model = None
    return _bert_model


def _extractive_summarize_bert(text, max_sentences=3):
    """
    Use BERT embeddings for extractive summarization by selecting most important sentences.
    
    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences to include in summary
    
    Returns:
        Summarized text with most important sentences
    """
    if not text or len(text.strip()) < 50:
        return text
    
    bert_model = _get_bert_model()
    if bert_model is None:
        return text[:200] + "..." if len(text) > 200 else text
    
    try:
        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= max_sentences:
            return text
        
        # Get embeddings for each sentence
        sentence_embeddings = bert_model.encode(sentences)
        
        # Get embedding for the full text (average of all sentences)
        full_text_embedding = sentence_embeddings.mean(axis=0)
        
        # Calculate cosine similarity between each sentence and the full text
        if not SKLEARN_AVAILABLE:
            # Fallback: use simple dot product for similarity
            similarities = np.dot(sentence_embeddings, full_text_embedding)
        else:
            similarities = cosine_similarity(
                sentence_embeddings,
                full_text_embedding.reshape(1, -1)
            ).flatten()
        
        # Select top N sentences with highest similarity
        top_indices = np.argsort(similarities)[-max_sentences:]
        top_indices = sorted(top_indices)  # Maintain original order
        
        # Reconstruct summary
        summary_sentences = [sentences[i] for i in top_indices]
        return ". ".join(summary_sentences) + "."
    except Exception as e:
        logger.warning(f"BERT extractive summarization failed: {e}. Using truncation.")
        return text[:200] + "..." if len(text) > 200 else text


def _summarize_text(text, max_length=150):
    """
    Summarize a single text using BERT/transformer model.
    Uses extractive summarization with BERT if available, otherwise uses abstractive.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of the summary
    
    Returns:
        Summarized text
    """
    if not text or len(text.strip()) < 50:
        return text
    
    # Try BERT extractive summarization first (if enabled)
    use_bert_extractive = os.getenv("USE_BERT_EXTRACTIVE", "false").lower() == "true"
    if use_bert_extractive:
        return _extractive_summarize_bert(text, max_sentences=3)
    
    # Otherwise use abstractive summarization (BART/BERT-based)
    summarizer = _get_summarizer()
    if summarizer is None:
        # Fallback: simple truncation
        return text[:max_length] + "..." if len(text) > max_length else text
    
    try:
        # Truncate input if too long (most models have token limits)
        max_input_length = 512
        if len(text) > max_input_length:
            text = text[:max_input_length]
        
        result = summarizer(text, max_length=max_length, min_length=30, do_sample=False)
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("summary_text", text)
        return text
    except Exception as e:
        logger.warning(f"Summarization failed: {e}. Using original text.")
        return text[:max_length] + "..." if len(text) > max_length else text


def summarize_results(search_results):
    """
    Summarize search results to reduce token consumption using BERT-based models.
    
    Args:
        search_results: Results from TavilySearchResults tool, typically a list of dicts
                      with keys: 'title', 'link', 'snippet', etc.
    
    Returns:
        A summarized version of the results. If input is a list, returns a list of
        condensed dictionaries with summarized snippets. If input is already 
        summarized or a string, returns as-is.
    """
    if not search_results:
        return []
    
    # If it's already a string or not a list, return as-is
    if not isinstance(search_results, list):
        return search_results
    
    # Summarize each result using BERT model
    summarized = []
    for item in search_results:
        if isinstance(item, dict):
            # Extract key fields
            title = item.get("title", "")
            link = item.get("link", item.get("url", ""))
            snippet = item.get("snippet", item.get("content", ""))
            
            # Summarize the snippet using BERT model if it's long enough
            if snippet and len(snippet) > 100:
                summarized_snippet = _summarize_text(snippet, max_length=150)
            else:
                summarized_snippet = snippet
            
            summarized_item = {
                "title": title,
                "link": link,
                "snippet": summarized_snippet
            }
            
            # Remove empty values
            summarized_item = {k: v for k, v in summarized_item.items() if v}
            if summarized_item:  # Only add if there's at least one field
                summarized.append(summarized_item)
        else:
            # If it's not a dict, try to summarize if it's a long string
            item_str = str(item)
            if len(item_str) > 500:
                summarized.append(_summarize_text(item_str, max_length=200))
            else:
                summarized.append(item)
    
    logger.debug(f"Summarized {len(search_results)} results to {len(summarized)} items using transformer model")
    return summarized

