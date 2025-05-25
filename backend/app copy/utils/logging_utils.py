"""
Utility functions for logging in the restaurant reservation system.
"""
import logging
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import logging.handlers

# Custom formatter that supports microseconds
class MicrosecondFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        if datefmt:
            # Handle microseconds separately
            if '%f' in datefmt:
                dt = datetime.fromtimestamp(record.created)
                # Replace %f with actual microseconds
                return dt.strftime(datefmt.replace('%f', '{:06d}'.format(dt.microsecond)))
        # Fall back to default formatting
        return super().formatTime(record, datefmt)

# Set up logging directory
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configure maximum log size and backup count
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Keep 5 backup files

# Create logger
logger = logging.getLogger(__name__)

# Add file handler for the current date
def get_file_handler(log_type="app"):
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = log_dir / f"{log_type}_{today}.log"
    
    file_handler = logging.FileHandler(str(file_path))
    file_handler.setLevel(logging.INFO)
    
    # Use the custom formatter that properly handles microseconds
    formatter = MicrosecondFormatter('%(asctime)s - %(message)s', '%Y-%m-%d %H:%M:%S,%f')
    file_handler.setFormatter(formatter)
    
    return file_handler

# Add handlers to logger
logger.addHandler(get_file_handler())

# Create a separate logger for tool calls
tool_logger = logging.getLogger("tool_calls")
tool_logger.setLevel(logging.INFO)
tool_logger.addHandler(get_file_handler("tool_calls"))

def log_llm_interaction(model: str, prompt: str, response: str, execution_time: float, metadata: Optional[Dict[str, Any]] = None):
    """
    Log an interaction with an LLM.
    
    Args:
        model: The name of the LLM model used
        prompt: The prompt sent to the LLM
        response: The response received from the LLM
        execution_time: The time taken for the LLM to respond in seconds
        metadata: Additional metadata about the interaction
    """
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "llm_interaction",
        "model": model,
        "prompt_length": len(prompt),
        "prompt": prompt,  # Log the full prompt instead of preview
        "response_length": len(response),
        "response": response,  # Log the full response instead of preview
        "execution_time_ms": round(execution_time * 1000, 2),
    }
    
    # Add metadata if provided
    if metadata:
        log_entry["metadata"] = metadata
        
    # Log as JSON
    tool_logger.info(f"LLM_CALL: {json.dumps(log_entry)}")

def log_tool_call(tool_name: str, params: Dict[str, Any], result: Any, execution_time: float):
    """
    Log a tool call with its parameters, result, and execution time.
    
    Args:
        tool_name: The name of the tool being called
        params: The parameters passed to the tool
        result: The result returned by the tool
        execution_time: The time taken to execute the tool call in seconds
    """
    # For very large results, get a summary instead of the full text
    result_summary = result
    if isinstance(result, str) and len(result) > 10000:
        result_summary = result[:5000] + "..." + result[-5000:]
    
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "tool_call",
        "tool_name": tool_name,
        "params": params,
        "result": result,  # Log full result
        "result_summary": result_summary,  # Keep a summary for very large results
        "execution_time_ms": round(execution_time * 1000, 2)
    }
    
    # Log as JSON
    tool_logger.info(f"TOOL_CALL: {json.dumps(log_entry)}")
