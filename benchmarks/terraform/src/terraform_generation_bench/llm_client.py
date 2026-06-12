"""LLM client wrapper for multiple providers."""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import openai
import requests

# Try to import anthropic, but handle if it fails
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Generated text
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API client."""
    
    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None):
        """Initialize OpenAI client.
        
        Args:
            model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    
    # Models that require max_completion_tokens instead of max_tokens
    _COMPLETION_TOKENS_MODELS = {"o1", "o1-mini", "o1-pro", "o3", "o3-mini", "o4-mini"}

    def _uses_completion_tokens(self) -> bool:
        """Return True if the model requires max_completion_tokens."""
        name = self.model.lower()
        for prefix in self._COMPLETION_TOKENS_MODELS:
            if name == prefix or name.startswith(f"{prefix}-"):
                return True
        if name.startswith("gpt-"):
            try:
                version = float(name.split("-")[1])
                if version >= 5:
                    return True
            except (IndexError, ValueError):
                pass
        return False

    def _is_reasoning_model(self) -> bool:
        """Return True if the model supports reasoning_effort."""
        name = self.model.lower()
        for prefix in self._COMPLETION_TOKENS_MODELS:
            if name == prefix or name.startswith(f"{prefix}-"):
                return True
        return False

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2000, reasoning_tokens: int = 10000, **kwargs) -> str:
        """Generate text using OpenAI API."""
        try:
            params = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Terraform expert. Generate only Terraform code blocks."},
                    {"role": "user", "content": prompt}
                ],
                **kwargs,
            )

            if self._is_reasoning_model():
                # Reasoning models only support temperature=1 (default), so omit it
                # Budget reasoning_tokens for thinking + max_tokens for output
                params["max_completion_tokens"] = reasoning_tokens + max_tokens
            elif self._uses_completion_tokens():
                # Newer models (gpt-5+) also only support temperature=1
                params["max_completion_tokens"] = max_tokens
            else:
                params["temperature"] = temperature
                params["max_tokens"] = max_tokens

            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")


class AnthropicClient(LLMClient):
    """Anthropic (Claude) API client."""
    
    # Common Anthropic model names (try these in order if one fails)
    # Order: requested model first, then variations, then fallbacks
    MODEL_ALIASES = {
        "claude-3-5-sonnet-20241022": [
            "claude-3-5-sonnet-20241022",  # Try requested model first
            "claude-3-5-sonnet-20240620",  # Try date variation
            "claude-3-5-sonnet",  # Try without date
            "claude-3-sonnet-20240229",  # Fallback to older sonnet
            "claude-3-haiku-20240307",  # Last resort fallback
        ],
        "claude-3-5-sonnet": [
            "claude-3-5-sonnet",  # Try requested model first
            "claude-3-5-sonnet-20241022",  # Try with latest date
            "claude-3-5-sonnet-20240620",  # Try with older date
            "claude-3-sonnet-20240229",  # Fallback to older sonnet
            "claude-3-haiku-20240307",  # Last resort fallback
        ],
        "claude-3-opus-20240229": ["claude-3-opus-20240229"],
        "claude-3-sonnet-20240229": ["claude-3-sonnet-20240229"],
        "claude-3-haiku-20240307": ["claude-3-haiku-20240307"],
    }
    
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        """Initialize Anthropic client.
        
        Args:
            model: Model name (e.g., "claude-3-5-sonnet-20241022", "claude-3-opus-20240229")
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key  # Store for later use
        # Don't create client here - create it lazily in generate() to ensure
        # we have the latest API key from environment
        self.client = None
    
    def _get_model_alternatives(self, model: str) -> list:
        """Get alternative model names to try if the primary fails."""
        # Check if we have aliases for this model
        for key, alternatives in self.MODEL_ALIASES.items():
            if model == key or model in alternatives:
                return alternatives
        
        # Universal fallbacks - try these if nothing else works
        # NOTE: claude-3-haiku-20240307 is known to work (tested successfully)
        universal_fallbacks = [
            "claude-3-haiku-20240307",  # Most basic, most widely available - CONFIRMED WORKING
            "claude-3-sonnet-20240229",  # Older but stable
            "claude-3-opus-20240229",    # Premium option
        ]
        
        # If no aliases, try the model as-is and common variations
        alternatives = [model]
        if "20241022" in model:
            alternatives.extend([
                model.replace("-20241022", "-20240620"),
                model.replace("-20241022", ""),
            ])
        elif "20240620" in model:
            alternatives.append(model.replace("-20240620", ""))
        
        # Add universal fallbacks at the end
        alternatives.extend(universal_fallbacks)
        return alternatives
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2000, reasoning_tokens: int = 10000, **kwargs) -> str:
        """Generate text using Anthropic API.

        Uses direct HTTP requests since the SDK has issues with model names.
        Extended thinking is enabled with the given reasoning_tokens budget.
        """
        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please set it with: export ANTHROPIC_API_KEY='your-key-here'"
            )

        # Use direct HTTP requests (same approach as test_anthropic_direct.py that works)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Try the model and alternatives if it fails
        models_to_try = self._get_model_alternatives(self.model)
        last_error = None

        for model_name in models_to_try:
            try:
                # Extended thinking requires temperature=1 and
                # max_tokens > budget_tokens
                payload = {
                    "model": model_name,
                    "max_tokens": reasoning_tokens + max_tokens,
                    "temperature": 1,
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": reasoning_tokens,
                    },
                    "system": "You are a Terraform expert. Generate only Terraform code blocks.",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }

                # Add any additional kwargs
                for key, value in kwargs.items():
                    if key not in payload:
                        payload[key] = value

                # Retry logic for 429 errors
                max_retries = 3
                for retry in range(max_retries):
                    response = requests.post(url, headers=headers, json=payload, timeout=120)

                    if response.status_code == 200:
                        data = response.json()
                        # If we used a different model, log it
                        if model_name != self.model:
                            import sys
                            print(f"[INFO] Used model '{model_name}' instead of '{self.model}'", file=sys.stderr)
                        # Extract the text block (skip thinking blocks)
                        for block in data["content"]:
                            if block.get("type") == "text":
                                return block["text"]
                        # Fallback: return first block's text if no type=text found
                        return data["content"][0].get("text", "")
                    elif response.status_code == 429:
                        # Rate limited - check Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            wait_time = int(retry_after)
                        else:
                            wait_time = 2 ** retry  # Exponential backoff: 1s, 2s, 4s

                        if retry < max_retries - 1:
                            import sys
                            print(f"[INFO] Rate limited (429), retrying in {wait_time}s (attempt {retry + 1}/{max_retries})", file=sys.stderr)
                            time.sleep(wait_time)
                            continue
                        else:
                            last_error = f"429: Rate limited after {max_retries} retries"
                            break
                    elif response.status_code == 401:
                        raise Exception(
                            f"Anthropic API authentication error (401). "
                            f"Please check your ANTHROPIC_API_KEY environment variable."
                        )
                    elif response.status_code == 404:
                        # Try next model
                        last_error = f"404: {response.text[:200]}"
                        break
                    else:
                        # For other errors, try next model but log it
                        last_error = f"{response.status_code}: {response.text[:200]}"
                        break
                    
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {e}"
                continue
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                continue
        
        # If all models failed, raise with helpful message
        api_key_preview = "set" if os.getenv("ANTHROPIC_API_KEY") else "NOT SET"
        api_key_value = os.getenv("ANTHROPIC_API_KEY", "")
        api_key_display = f"{api_key_value[:10]}..." if api_key_value and len(api_key_value) > 10 else "NOT SET"
        
        raise Exception(
            f"Anthropic API error: None of the tried models are available. "
            f"\n\nRequested model: '{self.model}'"
            f"\nModels tried: {', '.join(models_to_try)}"
            f"\nLast error: {last_error}"
            f"\nAPI Key: {api_key_preview} ({api_key_display})"
            f"\n\nPossible solutions:"
            f"\n1. Verify your API key is correct: echo $ANTHROPIC_API_KEY"
            f"\n2. Check your Anthropic account has access to Claude models"
            f"\n3. Try using OpenAI instead: --provider openai --model gpt-4"
            f"\n4. Check Anthropic API status: https://status.anthropic.com/"
            f"\n5. Verify your account region/endpoint supports these models"
        )


class EdgeeClient(LLMClient):
    """Edgee API client - OpenAI-compatible with compression."""

    def __init__(self, model: str = "claude-sonnet-4-5", api_key: Optional[str] = None):
        """Initialize Edgee client.

        Args:
            model: Model name (e.g., "claude-sonnet-4-5", "gpt-4o")
            api_key: Edgee API key (defaults to EDGEE_API_KEY env var)
        """
        self.model = model
        self.client = openai.OpenAI(
            base_url="https://api.edgee.ai/v1",
            api_key=api_key or os.getenv("EDGEE_API_KEY"),
            default_headers={
                "x-edgee-enable-compression": "true",
                "x-edgee-compression-rate": "0.8",
                "x-edgee-tags": "sre-skills-bench,evaluation",
            }
        )

    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2000, reasoning_tokens: int = 10000, **kwargs) -> str:
        """Generate text using Edgee API (OpenAI-compatible)."""
        try:
            params = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a Terraform expert. Generate only Terraform code blocks."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Edgee API error: {e}")


class OpenRouterClient(LLMClient):
    """OpenRouter API client - provides access to multiple LLM providers."""
    
    @staticmethod
    def get_available_models(api_key: Optional[str] = None) -> list:
        """Fetch available models from OpenRouter API.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            
        Returns:
            List of available model IDs
        """
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return []
        
        try:
            url = "https://openrouter.ai/api/v1/models"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model.get("id") for model in data.get("data", []) if model.get("id")]
            return []
        except Exception:
            return []
    
    def __init__(self, model: str, api_key: Optional[str] = None):
        """Initialize OpenRouter client.
        
        Args:
            model: Model name (e.g., "google/gemini-pro", "meta-llama/llama-3-70b-instruct")
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Please set it with: export OPENROUTER_API_KEY='your-key-here'"
            )
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 2000, reasoning_tokens: int = 10000, **kwargs) -> str:
        """Generate text using OpenRouter API.

        OpenRouter uses OpenAI-compatible API format.
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/prompt-to-terraform",  # Optional: for tracking
            "X-Title": "Terraform LLM Benchmark"  # Optional: for tracking
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a Terraform expert. Generate only Terraform code blocks."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # Retry logic for 429 errors
        max_retries = 3
        last_error = None

        for retry in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)

                # Check for 429 before raise_for_status
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = 2 ** retry  # Exponential backoff: 1s, 2s, 4s

                    if retry < max_retries - 1:
                        import sys
                        print(f"[INFO] Rate limited (429), retrying in {wait_time}s (attempt {retry + 1}/{max_retries})", file=sys.stderr)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise requests.exceptions.HTTPError(f"Rate limited (429) after {max_retries} retries", response=response)

                response.raise_for_status()

                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"Unexpected response format: {data}")

            except requests.exceptions.HTTPError as e:
                # Non-retryable HTTP error - save and break retry loop
                last_error = e
                break
            except requests.exceptions.RequestException as e:
                last_error = e
                break
            except Exception as e:
                last_error = e
                break

        # If we got here, all retries failed - handle the last error
        if isinstance(last_error, requests.exceptions.HTTPError):
            e = last_error
            error_msg = f"OpenRouter API HTTP error: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    if "error" in error_data:
                        error_msg += f" - {error_data['error']}"

                    # Handle payment/credit errors (402)
                    if e.response.status_code == 402:
                        error_msg += "\n\n💳 OpenRouter Credit/Payment Issue:"
                        error_msg += "\n   - Your account doesn't have enough credits for this request"
                        error_msg += "\n   - Note: Parallel execution can deplete credits faster"
                        error_msg += "\n   - Solutions:"
                        error_msg += "\n     1. Add credits: https://openrouter.ai/settings/credits"
                        error_msg += "\n     2. Upgrade to paid account"
                        error_msg += "\n     3. Reduce --max-workers (e.g., --max-workers 1 or 2)"
                        error_msg += "\n     4. Use a model with lower token costs"
                        error_msg += "\n     5. Reduce max_tokens in terraform_generator.py"
                        if "metadata" in error_data and "provider_name" in error_data.get("metadata", {}):
                            error_msg += f"\n   - Provider: {error_data['metadata']['provider_name']}"

                    # If model not found, suggest fetching available models
                    elif (e.response.status_code in [400, 404] and
                        ("not a valid model" in str(error_data).lower() or
                         "no endpoints found" in str(error_data).lower())):
                        available_models = self.get_available_models(self.api_key)
                        if available_models:
                            # Filter for similar models
                            model_parts = self.model.lower().split("/")
                            similar = [m for m in available_models if any(part in m.lower() for part in model_parts)]
                            if similar:
                                error_msg += f"\n\nSimilar available models: {', '.join(similar[:5])}"
                            else:
                                error_msg += f"\n\nExample available models: {', '.join(available_models[:10])}"
                        else:
                            error_msg += "\n\nTip: Use 'python benchmark_cli.py list-models' to see all available models"
                            error_msg += "\n      Or check: https://openrouter.ai/models"
                except:
                    error_msg += f" - {e.response.text[:200]}"
            raise Exception(error_msg)
        elif isinstance(last_error, requests.exceptions.RequestException):
            raise Exception(f"OpenRouter API request error: {last_error}")
        elif last_error:
            raise Exception(f"OpenRouter API error: {last_error}")
        else:
            raise Exception("OpenRouter API error: Unknown error occurred")


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    # Model name mappings for OpenRouter fallback
    OPENROUTER_MODEL_MAP = {
        # OpenAI models
        "gpt-4": "openai/gpt-4",
        "gpt-4-turbo": "openai/gpt-4-turbo",
        "gpt-4o": "openai/gpt-4o",
        "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
        # Anthropic models
        "claude-3-5-sonnet-20241022": "anthropic/claude-3.5-sonnet",
        "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-3-opus-20240229": "anthropic/claude-opus-4",
        "claude-3-opus": "anthropic/claude-opus-4",
        "claude-3-sonnet-20240229": "anthropic/claude-3-sonnet",
        "claude-3-sonnet": "anthropic/claude-3-sonnet",
        "claude-3-haiku-20240307": "anthropic/claude-3-haiku",
        "claude-3-haiku": "anthropic/claude-3-haiku",
    }
    
    @staticmethod
    def _has_direct_api_key(provider: str) -> bool:
        """Check if direct provider API key is available.

        Args:
            provider: Provider name ("openai", "anthropic", "edgee")

        Returns:
            True if API key is available
        """
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "edgee":
            return bool(os.getenv("EDGEE_API_KEY"))
        return False
    
    @staticmethod
    def _get_openrouter_model_name(provider: str, model: str) -> Optional[str]:
        """Get OpenRouter model name for a provider/model combination.
        
        Args:
            provider: Provider name ("openai", "anthropic")
            model: Model name
            
        Returns:
            OpenRouter model name or None if not mappable
        """
        # Check direct mapping first
        if model in LLMClientFactory.OPENROUTER_MODEL_MAP:
            return LLMClientFactory.OPENROUTER_MODEL_MAP[model]
        
        # Try provider/model format
        if provider == "openai":
            return f"openai/{model}"
        elif provider == "anthropic":
            # Try common Anthropic model patterns
            if "claude" in model.lower():
                # Extract base name (e.g., "claude-3-5-sonnet" from "claude-3-5-sonnet-20241022")
                base_name = model.split("-202")[0] if "-202" in model else model
                return f"anthropic/{base_name}"
        
        return None
    
    @staticmethod
    def create_client(provider: str, model: str, api_key: Optional[str] = None,
                     use_openrouter_fallback: bool = True) -> LLMClient:
        """Create an LLM client for the specified provider.

        Smart routing:
        - Uses direct provider API key if available (OPENAI_API_KEY, ANTHROPIC_API_KEY, EDGEE_API_KEY)
        - Falls back to OpenRouter if direct key not available and use_openrouter_fallback=True

        Args:
            provider: Provider name ("openai", "anthropic", "edgee", "openrouter")
            model: Model name
            api_key: Optional API key (overrides environment check)
            use_openrouter_fallback: If True, fallback to OpenRouter when direct key unavailable

        Returns:
            LLMClient instance
        """
        provider = provider.lower()

        # If provider is explicitly "openrouter", always use OpenRouter
        if provider == "openrouter":
            return OpenRouterClient(model=model, api_key=api_key)

        # If provider is explicitly "edgee", always use Edgee
        if provider == "edgee":
            return EdgeeClient(model=model, api_key=api_key)
        
        # Check if we have a direct API key (or one was provided)
        has_direct_key = bool(api_key) or LLMClientFactory._has_direct_api_key(provider)
        has_openrouter_key = bool(os.getenv("OPENROUTER_API_KEY"))
        
        if has_direct_key:
            # Use direct provider - never fallback to OpenRouter if direct key is available
            if provider == "openai":
                return OpenAIClient(model=model, api_key=api_key)
            elif provider == "anthropic":
                return AnthropicClient(model=model, api_key=api_key)
            elif provider == "edgee":
                return EdgeeClient(model=model, api_key=api_key)
        elif use_openrouter_fallback and has_openrouter_key:
            # Fallback to OpenRouter only if:
            # 1. No direct key available
            # 2. OpenRouter key is set
            # 3. Fallback is enabled
            openrouter_model = LLMClientFactory._get_openrouter_model_name(provider, model)
            if openrouter_model:
                import sys
                print(f"[INFO] Using OpenRouter fallback for {provider}/{model} -> {openrouter_model}", 
                      file=sys.stderr)
                return OpenRouterClient(model=openrouter_model, api_key=None)  # Use env var
            else:
                # Can't map to OpenRouter, try direct provider anyway (will fail with clear error)
                if provider == "openai":
                    return OpenAIClient(model=model, api_key=api_key)
                elif provider == "anthropic":
                    return AnthropicClient(model=model, api_key=api_key)
                elif provider == "edgee":
                    return EdgeeClient(model=model, api_key=api_key)
        elif use_openrouter_fallback and not has_openrouter_key:
            # Direct key not available, but OpenRouter key also not set
            # Use direct provider - it will fail with a clear error about missing API key
            if provider == "openai":
                return OpenAIClient(model=model, api_key=api_key)
            elif provider == "anthropic":
                return AnthropicClient(model=model, api_key=api_key)
            elif provider == "edgee":
                return EdgeeClient(model=model, api_key=api_key)
        
        # No fallback available, use direct provider (will fail with clear error)
        if provider == "openai":
            return OpenAIClient(model=model, api_key=api_key)
        elif provider == "anthropic":
            return AnthropicClient(model=model, api_key=api_key)
        elif provider == "edgee":
            return EdgeeClient(model=model, api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}. Supported: openai, anthropic, edgee, openrouter")

