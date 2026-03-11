"""OpenRouter API integration with per-user response caching.

Provides Chat Completion API interface using OpenRouter service.
Implements user-isolated cache layer to prevent cross-user data leaks
and optimize repeated user queries (20-minute TTL).

Uses Django's cache framework for persistent session caching.
Supports multimodal messages with file attachments (images, documents).

Reference:
    https://openrouter.ai/api/documentation
    https://docs.djangoproject.com/en/5.2/topics/cache/
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import mimetypes
import base64  # Binary-to-base64 encoding for file transmission via text-only APIs
import hashlib  # Hash generation for cache keys and unique message identifiers
from django.core.cache import cache  # Django cache framework for per-user response storage

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
#OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# Potrzebna aktualna nazwa modelu z https://openrouter.ai/models (filter: Free)
# Przykład: "mistralai/mistral-7b-instruct:free" lub "google/flan-t5-xl:free"
#MODEL = "nvidia/llama-nemotron"
#####MODEL = "openai/gpt-oss-120b:free"
MODEL = "google/gemma-3-27b-it:free"
#MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
#MODEL = "mistralai/mistral-7b-instruct:free"

client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

def build_user_content(messages_obj):
    """Build multimodal message content with text and attachments.
    
    Constructs content array combining text message with base64-encoded
    file attachments (images, documents). Each attachment is serialized
    as data URL for transmission via OpenRouter API.
    
    Args:
        messages_obj (ChatMessage): Message containing text and attachments.
    
    Returns:
        list: Content array with text and attachment objects.
    
    Reference:
        https://openrouter.ai/docs#models
    """
    content = [{"type" : "text", "text" : messages_obj.content}]

    for att in messages_obj.attachments.all():
        file_path = att.file.path
        mime, _ = mimetypes.guess_type(file_path) # _ = ignore encoding info; focus on MIME type only
        # Default to binary stream if MIME type cannot be determined
        mime = mime or "application/octet-stream"
        with open(file_path, 'rb') as f:  # rb = read binary mode for all file types
            # Encode file content to base64 string for safe text transmission
            b64 = base64.b64encode(f.read()).decode('utf-8')
            if att.file_type == "img":
                # Image attachment: use data URL with embedded base64 content
                content.append({"type" : "image_url", 
                                "image_url" : f"data:{mime};base64,{b64}"
                                }) 
            else: 
                # Document attachment: use file data URL format
                content.append({"type" : "file", 
                                "filename" : att.file.name,
                                "file_data" : f"data:{mime};base64,{b64}"
                                })
        return content



def make_cache_key(message_obj) -> str:
    """Generate per-user cache key with direct user ID in key format.
    
    Creates cache key combining user ID prefix with hash of prompt content.
    Ensures strict cache isolation between users for privacy and prevents
    accidental cross-user data access.
    
    Key format: ai:{user_id}:{prompt_hash}
    - user_id: User identifier for cache isolation
    - prompt_hash: MD5 hash of message content
    
    Args:
        message_obj (ChatMessage): Message with session.user and content.
    
    Returns:
        str: Cache key format "ai:{user_id}:{md5_hash}" (explicit user separation).
    
    Reference:
        https://docs.djangoproject.com/en/5.2/topics/cache/#cache-key-warnings
    """
    # Extract user_id for explicit cache key isolation
    user_id = message_obj.session.user.id
    
    # Generate MD5 hash of prompt content
    prompt_hash = hashlib.md5(message_obj.content.encode()).hexdigest()
    
    # Return cache key with explicit user_id separation: ai:{user_id}:{hash}
    return f"ai:{user_id}:{prompt_hash}"


def ask_openrouter(message_obj):
    """Query OpenRouter API with per-user response caching.
    
    Generates per-user cache key from user ID and prompt content hash.
    Returns cached response if available (20-minute TTL), otherwise queries API.
    Ensures complete cache isolation between users for privacy.
    
    Args:
        message_obj (ChatMessage): Message with session.user and content.
    
    Returns:
        str: AI response text from cache or API call.
    
    Reference:
        https://docs.djangoproject.com/en/5.2/topics/cache/
    """
    # Generate unique per-user cache key incorporating user ID and prompt hash
    key = make_cache_key(message_obj)
    
    # Check cache first to avoid redundant API calls
    cached = cache.get(key)
    if cached:
        return cached
    
    if not OPENROUTER_API_KEY:
        return "Demo response (API key nie ustawiony): Dziękuję za pytanie: " + message_obj.content[:50] + "..."
    if not client:
        return "Demo response: Chatbot nie mógł połączyć się z API"
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":message_obj.content}],
            extra_body={"reasoning": {"enabled": True}}
        )
        answer = response.choices[0].message.content
        # Store response in per-user cache with 20-minute TTL (1200 seconds)
        # Each user's cache is independent, file-aware, ensuring data privacy
        cache.set(key, answer, timeout=60*20)
        return answer
    except Exception as e:
        return f"Blad OPENROUTER: {str(e)}"


