# Create a new file: process_utils.py
import asyncio
from typing import Any, Dict

async def create_windows_process(command: str, args: list, env: Dict[str, Any], cwd: str):
    """Workaround for Windows subprocess issues"""
    return await asyncio.create_subprocess_exec(
        command,
        *args,
        env=env,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        limit=1024 * 1024  # 1MB buffer
    )