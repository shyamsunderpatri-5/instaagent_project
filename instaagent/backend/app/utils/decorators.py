# backend/app/utils/decorators.py
import functools
import asyncio
import logging

logger = logging.getLogger(__name__)

def retry_on_exception(retries: int = 3, delay: float = 1.0):
    """
    Decorator for retrying both sync and async functions with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(retries):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        # Call sync function in threadpool to avoid blocking event loop
                        from functools import partial
                        loop = asyncio.get_running_loop()
                        return await loop.run_in_executor(None, partial(func, *args, **kwargs))
                except Exception as e:
                    last_exc = e
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} due to {e}")
                    if i < retries - 1:
                        await asyncio.sleep(delay * (2 ** i))
            raise last_exc
        return wrapper
    return decorator
