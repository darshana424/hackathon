# src/utils/llm_resolver.py
"""
Centralized LLM Configuration Resolver.
Implements cascading field fallback: if one API key field is empty,
checks the next field, and so on. Single source of truth for all
LLM-related key resolution across the entire pipeline.
"""

from src.utils.logger import logger
from src.config import config


def is_valid_key(key) -> bool:
    """Check if an API key is real (not a placeholder or empty)."""
    if not key:
        return False
    key_str = str(key)
    if len(key_str) < 10:
        return False
    placeholder_markers = ["your_", "placeholder", "xxx", "test_key", "REPLACE", "INSERT"]
    return not any(marker.lower() in key_str.lower() for marker in placeholder_markers)


def resolve_api_key(llm_config: dict, target_provider: str = None) -> tuple[str, str]:
    """
    Cascading API key resolution. Returns (provider, api_key).
    
    Checks fields in this order for each provider:
      1. llm_config["api_key"] (if provider matches)
      2. llm_config["{provider}_key"]
      3. Environment / config defaults
      
    If target_provider is specified, tries that first.
    Otherwise walks the full fallback chain.
    """
    target_provider = target_provider or llm_config.get("provider", "gemini")
    target_provider = target_provider.lower()
    
    # Build ordered fallback chain starting with the preferred provider
    fallback_chain = ["gemini", "openai", "openrouter", "ollama"]
    if target_provider in fallback_chain:
        fallback_chain.remove(target_provider)
    chain = [target_provider] + fallback_chain
    
    for provider in chain:
        key = _resolve_key_for_provider(llm_config, provider)
        if provider == "ollama":
            return provider, "ollama"
        if is_valid_key(key):
            logger.info(f"LLM Resolver: Selected provider '{provider}' (requested: '{target_provider}')")
            return provider, key
    
    # Final fallback to ollama
    logger.warning("LLM Resolver: No valid API keys found. Falling back to Ollama.")
    return "ollama", "ollama"


def _resolve_key_for_provider(llm_config: dict, provider: str) -> str | None:
    """
    Cascading field check for a single provider. Checks multiple field names.
    """
    candidates = []
    
    # Field 1: Direct provider key field  (e.g., "gemini_key", "openai_key")
    candidates.append(llm_config.get(f"{provider}_key"))
    
    # Field 2: Generic "api_key" if this provider is the configured one
    if llm_config.get("provider", "").lower() == provider:
        candidates.append(llm_config.get("api_key"))
    
    # Field 3: Alternative naming conventions
    alt_names = {
        "openai": ["openai_api_key", "oai_key"],
        "gemini": ["gemini_api_key", "google_key", "google_api_key"],
        "openrouter": ["openrouter_api_key", "or_key"],
    }
    for alt in alt_names.get(provider, []):
        candidates.append(llm_config.get(alt))
    
    # Field 4: Environment / config defaults
    try:
        if provider == "openai" and config.OPENAI_API_KEY:
            val = config.OPENAI_API_KEY
            candidates.append(val.get_secret_value() if hasattr(val, 'get_secret_value') else str(val))
        elif provider == "gemini" and config.GEMINI_API_KEY:
            val = config.GEMINI_API_KEY
            candidates.append(val.get_secret_value() if hasattr(val, 'get_secret_value') else str(val))
    except Exception:
        pass
    
    # Return the first valid candidate
    for key in candidates:
        if is_valid_key(key):
            return key
    
    return None


def build_call_config(llm_config: dict, provider: str = None) -> dict:
    """
    Build a complete call config with resolved provider and API key.
    This is the single entry point for all LLM callers.
    """
    resolved_provider, resolved_key = resolve_api_key(llm_config, provider)
    
    call_config = llm_config.copy()
    call_config["provider"] = resolved_provider
    call_config["api_key"] = resolved_key
    
    # Ensure ollama config is always present
    if "ollama_host" not in call_config:
        call_config["ollama_host"] = getattr(config, "OLLAMA_HOST", "http://localhost:11434")
    if "ollama_model" not in call_config:
        call_config["ollama_model"] = "llama3"
    
    return call_config


def call_llm_with_fallback(prompt: str, llm_config: dict, system_prompt: str = None) -> str:
    """
    Universal LLM caller with full provider fallback chain.
    Tries each provider in order until one succeeds.
    """
    from src.content.page_generator import _call_openai, _call_gemini, _call_ollama, _call_openrouter
    
    primary = llm_config.get("provider", "gemini").lower()
    fallback_chain = ["gemini", "openai", "openrouter", "ollama"]
    if primary in fallback_chain:
        fallback_chain.remove(primary)
    chain = [primary] + fallback_chain
    
    for provider in chain:
        key = _resolve_key_for_provider(llm_config, provider)
        
        if provider != "ollama" and not is_valid_key(key):
            continue
        
        try:
            call_cfg = llm_config.copy()
            call_cfg["provider"] = provider
            call_cfg["api_key"] = key if provider != "ollama" else "ollama"
            
            result = None
            if provider == "openai":
                result = _call_openai(prompt, call_cfg)
            elif provider == "gemini":
                result = _call_gemini(prompt, call_cfg)
            elif provider == "ollama":
                result = _call_ollama(prompt, call_cfg)
            elif provider == "openrouter":
                result = _call_openrouter(prompt, call_cfg)
            
            if result and not result.startswith("Error:"):
                return result
                
        except Exception as e:
            logger.warning(f"LLM Fallback: {provider} failed ({e}). Trying next...")
            continue
    
    raise RuntimeError("All LLM providers exhausted. No valid response obtained.")
