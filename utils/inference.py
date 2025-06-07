import os
import openai
import anthropic
import aiohttp
import json
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
import asyncio
import requests

async def generate_text(model: str, prompt: str, max_tokens: int = 8000, temperature: float = 0) -> str:
    """
    Asynchronously generate text using various AI models.
    
    :param model: The name of the model to use (e.g., "gpt-3.5-turbo", "claude-2", "meta-llama/Llama-2-70b-chat-hf")
    :param prompt: The input prompt for text generation
    :param max_tokens: Maximum number of tokens to generate
    :param temperature: Controls randomness in generation (0.0 to 1.0)
    :return: Generated text as a string
    """
    
    # OpenAI models
    if model.startswith("o1") or model.startswith("o3") or model.startswith("o4"):
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        async_openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        response = await async_openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
          
        )
        return response.choices[0].message.content.strip()
    
    elif model.startswith("gpt-"):
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        async_openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        response = await async_openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    
    # Anthropic (Claude) models
    elif model.startswith("claude-"):
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
            
        async def run_anthropic():
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            if model.startswith("claude-3"):
                response = client.messages.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.content[0].text.strip()
            else:
                response = client.completions.create(
                    model=model,
                    prompt=f"Human: {prompt}\n\nAssistant:",
                    max_tokens_to_sample=max_tokens,
                    temperature=temperature
                )
                return response.completion.strip()
        
        return await run_anthropic()
    
    # DeepInfra models
    elif model.startswith("meta-llama/") or model.startswith("deepseek-ai") or model.startswith("Qwen/") or model.startswith("Meta-Llama"):
        deepinfra_api_key = os.getenv('DEEPINFRA_API_KEY')
        if not deepinfra_api_key:
            raise ValueError("DEEPINFRA_API_KEY environment variable is not set")
            
        deepinfra_client = AsyncOpenAI(
            api_key=deepinfra_api_key,
            base_url="https://api.deepinfra.com/v1/openai"
        )
        
        response = await deepinfra_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    
    # DeepSeek models
    elif model.startswith("deepseek-"):
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        if not deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
            
        deepseek_client = AsyncOpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        
        try:
            response = await deepseek_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:  
            print(f"An error occurred while generating text with DeepSeek model: {e}")
            raise
    
    else:
        raise ValueError(f"Unsupported model: {model}")
