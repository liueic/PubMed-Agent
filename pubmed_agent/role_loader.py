"""
Role prompt loader for PubMed Agent.
Loads role-specific system prompts from markdown files.
"""

import os
from pathlib import Path
from typing import Optional


def find_project_root() -> Path:
    """Find the project root directory (where .env or pyproject.toml exists)."""
    current_dir = Path.cwd()
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / '.env').exists() or (parent / 'pyproject.toml').exists():
            return parent
    return current_dir


def load_role_prompt(role_name: Optional[str] = None, role_file_path: Optional[str] = None) -> Optional[str]:
    """
    Load role prompt from a markdown file.
    
    Args:
        role_name: Name of the role (e.g., "Synapse Scholar") - will look for "agents/{role_name}.md"
        role_file_path: Direct path to the role file (overrides role_name)
        
    Returns:
        Role prompt content as string, or None if not found
    """
    project_root = find_project_root()
    
    # Determine file path
    if role_file_path:
        # Use provided path (can be absolute or relative)
        if os.path.isabs(role_file_path):
            role_path = Path(role_file_path)
        else:
            role_path = project_root / role_file_path
    elif role_name:
        # Look for role in agents/ directory
        role_path = project_root / "agents" / f"{role_name}.md"
    else:
        # Default: try to find "Synapse Scholar.md" in agents/ directory
        # This allows automatic loading if the file exists
        role_path = project_root / "agents" / "Synapse Scholar.md"
    
    # Try to load the file
    if role_path.exists() and role_path.is_file():
        try:
            with open(role_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load role prompt from {role_path}: {e}")
            return None
    else:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Role prompt file not found: {role_path}")
        return None


def combine_role_prompt_with_system_prompt(
    system_prompt: str,
    role_prompt: Optional[str] = None,
    role_name: Optional[str] = None,
    role_file_path: Optional[str] = None
) -> str:
    """
    Combine role prompt with system prompt.
    
    Args:
        system_prompt: The base system prompt
        role_prompt: Pre-loaded role prompt content (optional)
        role_name: Name of the role to load (optional, if role_prompt not provided)
        role_file_path: Path to role file (optional, if role_prompt not provided)
        
    Returns:
        Combined prompt with role prompt prepended
    """
    # Load role prompt if not provided
    if role_prompt is None:
        role_prompt = load_role_prompt(role_name=role_name, role_file_path=role_file_path)
    
    # If no role prompt found, return original system prompt
    if not role_prompt:
        return system_prompt
    
    # Combine: role prompt first, then system prompt
    # Remove "## System Prompt" header if present in role prompt
    role_content = role_prompt.strip()
    if role_content.startswith("## System Prompt"):
        # Remove the header line
        lines = role_content.split('\n')
        role_content = '\n'.join(lines[1:]).strip()
    
    # Combine with system prompt
    combined = f"{role_content}\n\n---\n\n{system_prompt}"
    
    return combined

