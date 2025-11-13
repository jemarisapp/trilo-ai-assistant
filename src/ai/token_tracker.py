"""
Token Usage Tracking for AI Operations
Monitors and logs token consumption to optimize costs
"""

import time
from typing import Dict, Optional
from functools import wraps
import tiktoken

# Token costs per 1M tokens (as of Nov 2024)
PRICING = {
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M input tokens
        "output": 10.00  # $10.00 per 1M output tokens
    },
    "gpt-4o-mini": {
        "input": 0.150,  # $0.15 per 1M input tokens
        "output": 0.600  # $0.60 per 1M output tokens
    }
}


class TokenTracker:
    """Track token usage across AI operations"""
    
    def __init__(self):
        self.usage_log = []
        self.encoding = tiktoken.encoding_for_model("gpt-4o")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate cost in USD for token usage"""
        if model not in PRICING:
            model = "gpt-4o-mini"  # Default
        
        input_cost = (input_tokens / 1_000_000) * PRICING[model]["input"]
        output_cost = (output_tokens / 1_000_000) * PRICING[model]["output"]
        
        return input_cost + output_cost
    
    def log_usage(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float
    ):
        """Log token usage for an operation"""
        cost = self.calculate_cost(input_tokens, output_tokens, model)
        
        entry = {
            "timestamp": time.time(),
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "duration_ms": duration_ms
        }
        
        self.usage_log.append(entry)
        
        # Also print for monitoring
        print(f"[Token Usage] {operation} | {model} | "
              f"In: {input_tokens} Out: {output_tokens} | "
              f"Cost: ${cost:.5f} | {duration_ms:.0f}ms")
    
    def get_summary(self) -> Dict:
        """Get summary of token usage"""
        if not self.usage_log:
            return {"total_cost": 0, "total_tokens": 0, "operations": 0}
        
        total_cost = sum(entry["cost_usd"] for entry in self.usage_log)
        total_tokens = sum(entry["total_tokens"] for entry in self.usage_log)
        
        # Group by operation
        by_operation = {}
        for entry in self.usage_log:
            op = entry["operation"]
            if op not in by_operation:
                by_operation[op] = {
                    "count": 0,
                    "total_tokens": 0,
                    "total_cost": 0
                }
            by_operation[op]["count"] += 1
            by_operation[op]["total_tokens"] += entry["total_tokens"]
            by_operation[op]["total_cost"] += entry["cost_usd"]
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "operations": len(self.usage_log),
            "by_operation": by_operation
        }
    
    def reset(self):
        """Reset usage log"""
        self.usage_log = []


# Global tracker instance
_tracker = TokenTracker()


def get_tracker() -> TokenTracker:
    """Get the global token tracker"""
    return _tracker


def track_tokens(operation_name: str, model: str = "gpt-4o-mini"):
    """
    Decorator to track token usage for AI operations
    
    Usage:
        @track_tokens("setup_help", "gpt-4o")
        async def my_ai_function(prompt):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            tracker = get_tracker()
            
            # Get prompt from args (usually first arg or in kwargs)
            prompt = ""
            if args and isinstance(args[0], str):
                prompt = args[0]
            elif "prompt" in kwargs:
                prompt = kwargs["prompt"]
            
            input_tokens = tracker.estimate_tokens(prompt)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Estimate output tokens
            output_tokens = tracker.estimate_tokens(str(result)) if result else 0
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log usage
            tracker.log_usage(operation_name, model, input_tokens, output_tokens, duration_ms)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            tracker = get_tracker()
            
            # Get prompt from args
            prompt = ""
            if args and isinstance(args[0], str):
                prompt = args[0]
            elif "prompt" in kwargs:
                prompt = kwargs["prompt"]
            
            input_tokens = tracker.estimate_tokens(prompt)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Estimate output tokens
            output_tokens = tracker.estimate_tokens(str(result)) if result else 0
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log usage
            tracker.log_usage(operation_name, model, input_tokens, output_tokens, duration_ms)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def estimate_tokens(text: str) -> int:
    """Quick helper to estimate tokens for any text"""
    return get_tracker().estimate_tokens(text)



