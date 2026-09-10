"""A shared thread pool for fire-and-forget background work (statement processing).

Deliberately not Celery/RQ/a task queue with its own broker — that's real
infrastructure this project doesn't need yet given the budget constraint. A
plain ThreadPoolExecutor is enough to stop one slow file's LLM calls from
blocking every other file in the same upload batch, which is the actual problem.
"""
from concurrent.futures import ThreadPoolExecutor

EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="statement-processor")
