import os
import anthropic
import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import asyncio

# Config Loading
_config = None
_model_mapping = None
_providers = None

def _load_config():
    """Load the inference configuration from config.json."""
    global _config, _model_mapping, _providers
    if _config is None:
        try:
            with open("config.json", "r") as f:
                _config = json.load(f)
            _providers = _config.get("llm_providers", {})
            _model_mapping = _config.get("model_provider_mapping", {})
            if not _providers or not _model_mapping:
                raise ValueError("`llm_providers` or `model_provider_mapping` is missing from config.json")
        except FileNotFoundError:
            raise FileNotFoundError("config.json not found. Please ensure it exists in the project directory.")
        except json.JSONDecodeError:
            raise ValueError("config.json is not a valid JSON file.")


async def generate_text(model: str, prompt: str, max_tokens: int = 8000, temperature: float = 0) -> str:
    """
    Asynchronously generate text using a provider defined in config.json.

    This function reads the configured model, determines the correct provider for the
    given model, and makes the API call. It handles both OpenAI-compatible APIs
    and special cases like Anthropic within this single function.
    
    :param model: The name of the model to use (must be defined in config.json)
    :param prompt: The input prompt for text generation
    :param max_tokens: Maximum number of tokens to generate
    :param temperature: Controls randomness in generation
    :return: Generated text as a string
    """
    _load_config()

    # 1. Find the provider for the requested model
    provider_name = _model_mapping.get(model)
    if not provider_name:
        raise ValueError(f"Model '{model}' not found in 'model_provider_mapping' in config.json.")

    # 2. Get the configuration for that provider
    provider_config = _providers.get(provider_name)
    if not provider_config:
        raise ValueError(f"Provider '{provider_name}' for model '{model}' not found in 'llm_providers' in config.json.")

    # 3. Get the API key from environment variables
    api_key_env = provider_config.get("api_key_env")
    if api_key_env == "":
        api_key = "dummy-key"
    else:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"API key environment variable '{api_key_env}' is not set.")

    provider_type = provider_config.get("type")
    # 4. Handle generation based on provider type within this function
    try:
        if provider_type in ["openai", "openai_compatible"]:
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=provider_config.get("base_url")  # Works for both OpenAI and compatible APIs
            )
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()

        elif provider_type == "anthropic":
            client = anthropic.Anthropic(api_key=api_key)
            
            async def do_request():
                if "claude-3" in model: # Use new API
                    response = client.messages.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    return response.content[0].text.strip()
                else: # Use legacy API
                    response = client.completions.create(
                        model=model,
                        prompt=f"\n\nHuman: {prompt}\n\nAssistant:",
                        max_tokens_to_sample=max_tokens,
                        temperature=temperature
                    )
                    return response.completion.strip()

            return await do_request()

        else:
            raise ValueError(f"Unsupported provider type '{provider_type}' for provider '{provider_name}'.")
            
    except Exception as e:
        print(f"An error occurred while generating text with model '{model}' from provider '{provider_name}': {e}")
        raise