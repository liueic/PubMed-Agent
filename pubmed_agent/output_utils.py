"""
Output utilities for saving query results to Markdown files.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def response_to_markdown(response: Dict[str, Any], question: Optional[str] = None) -> str:
    """
    Convert a response dictionary to Markdown format.
    
    Args:
        response: Response dictionary from PubMedAgent.query()
        question: Optional question text (if not in response)
        
    Returns:
        Markdown formatted string
    """
    question_text = question or response.get('question', 'Unknown Question')
    success = response.get('success', False)
    language = response.get('language', 'unknown')
    prompt_type = response.get('prompt_type', 'unknown')
    thread_id = response.get('thread_id', 'N/A')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    md_lines = []
    
    # Header
    md_lines.append("# PubMed Agent Query Result")
    md_lines.append("")
    md_lines.append(f"**Generated:** {timestamp}")
    md_lines.append("")
    
    # Metadata
    md_lines.append("## Metadata")
    md_lines.append("")
    md_lines.append(f"- **Question:** {question_text}")
    md_lines.append(f"- **Status:** {'[SUCCESS]' if success else '[FAILED]'}")
    md_lines.append(f"- **Language:** {language}")
    md_lines.append(f"- **Prompt Type:** {prompt_type}")
    md_lines.append(f"- **Thread ID:** `{thread_id}`")
    md_lines.append("")
    
    if success:
        # Answer section
        answer = response.get('answer', 'No answer provided')
        md_lines.append("## Answer")
        md_lines.append("")
        md_lines.append(answer)
        md_lines.append("")
        
        # Intermediate steps (if available)
        intermediate_steps = response.get('intermediate_steps', [])
        if intermediate_steps:
            md_lines.append("## Reasoning Process")
            md_lines.append("")
            for i, step in enumerate(intermediate_steps, 1):
                md_lines.append(f"### Step {i}")
                md_lines.append("")
                if isinstance(step, tuple) and len(step) >= 2:
                    action, observation = step[0], step[1]
                    if hasattr(action, 'tool'):
                        md_lines.append(f"**Tool:** `{action.tool}`")
                        md_lines.append("")
                    if hasattr(action, 'tool_input'):
                        md_lines.append(f"**Input:**")
                        md_lines.append("```")
                        md_lines.append(str(action.tool_input))
                        md_lines.append("```")
                        md_lines.append("")
                    md_lines.append("**Observation:**")
                    md_lines.append("```")
                    observation_str = str(observation)
                    # Truncate very long observations
                    if len(observation_str) > 2000:
                        observation_str = observation_str[:2000] + "\n... (truncated)"
                    md_lines.append(observation_str)
                    md_lines.append("```")
                    md_lines.append("")
    else:
        # Error section
        error_msg = response.get('error', 'Unknown error')
        error_details = response.get('error_details', {})
        
        md_lines.append("## Error")
        md_lines.append("")
        md_lines.append(f"**Error Message:** {error_msg}")
        md_lines.append("")
        
        if error_details:
            md_lines.append("### Error Details")
            md_lines.append("")
            if error_details.get('type'):
                md_lines.append(f"- **Type:** {error_details['type']}")
            if error_details.get('status_code'):
                md_lines.append(f"- **HTTP Status Code:** {error_details['status_code']}")
            if error_details.get('request_url'):
                md_lines.append(f"- **Request URL:** `{error_details['request_url']}`")
            if error_details.get('details'):
                md_lines.append("")
                md_lines.append("**Details:**")
                md_lines.append("")
                md_lines.append(error_details['details'])
            md_lines.append("")
    
    return "\n".join(md_lines)


def save_response_to_markdown(
    response: Dict[str, Any],
    output_dir: Optional[str] = None,
    filename: Optional[str] = None
) -> str:
    """
    Save response to a Markdown file.
    
    Args:
        response: Response dictionary from PubMedAgent.query()
        output_dir: Output directory (default: project root)
        filename: Optional filename (default: auto-generated with timestamp)
        
    Returns:
        Path to the saved file
    """
    # Determine output directory
    if output_dir is None:
        # Try to find project root (where .env or pyproject.toml exists)
        current_dir = Path.cwd()
        project_root = current_dir
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / '.env').exists() or (parent / 'pyproject.toml').exists():
                project_root = parent
                break
        output_dir = str(project_root)
    else:
        output_dir = str(output_dir)
    
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        question = response.get('question', 'query')
        # Sanitize question for filename - remove special characters
        import re
        safe_question = re.sub(r'[^\w\s-]', '', question[:50])  # Remove special chars
        safe_question = re.sub(r'[-\s]+', '_', safe_question)  # Replace spaces and dashes with underscore
        safe_question = safe_question.strip('_')  # Remove leading/trailing underscores
        if not safe_question:
            safe_question = 'query'
        filename = f"pubmed_query_{timestamp}_{safe_question}.md"
    
    # Ensure filename ends with .md
    if not filename.endswith('.md'):
        filename += '.md'
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate markdown content
    question = response.get('question', 'Unknown Question')
    markdown_content = response_to_markdown(response, question)
    
    # Write to file
    file_path = output_path / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return str(file_path)

