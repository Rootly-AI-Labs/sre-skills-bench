"""Terraform code generator using LLMs."""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from terraform_generation_bench.llm_client import LLMClient
from terraform_generation_bench.runner.utils import log_info, log_warn, log_error


class TerraformGenerator:
    """Generates Terraform code from prompts using LLMs."""
    
    def __init__(self, llm_client: LLMClient):
        """Initialize the generator.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client
    
    def extract_code_blocks(self, text: str) -> Dict[str, str]:
        """Extract code blocks from LLM response.
        
        Handles multiple formats:
        - ```main.tf\ncode\n```
        - ```terraform\ncode\n```
        - File: main.tf\ncode
        - # main.tf\ncode
        
        Args:
            text: LLM response text
            
        Returns:
            Dictionary mapping filename to code content
        """
        files = {}
        
        log_info(f"Extracting code blocks from LLM response (length: {len(text)} chars)")
        
        # Method 1: Standard markdown code blocks with filename
        # Pattern: ```main.tf\ncode\n``` or ```terraform\ncode\n``` or ```hcl\ncode\n```
        pattern1 = r'```(?:(\w+\.tf)|terraform|hcl)?\s*\n(.*?)```'
        matches = re.finditer(pattern1, text, re.DOTALL | re.IGNORECASE)

        for match in matches:
            filename = match.group(1)
            code = match.group(2).strip()

            # If no filename in the ``` marker, check if the first line is a
            # comment like "# main.tf" — common pattern from Claude/Anthropic
            if not filename and code:
                first_line_match = re.match(r'^#\s*(\w+\.tf)\s*$', code.split('\n')[0])
                if first_line_match:
                    filename = first_line_match.group(1)
                    # Remove the comment line from the code
                    code = '\n'.join(code.split('\n')[1:]).strip()

            if filename:
                if not filename.endswith('.tf'):
                    filename = f"{filename}.tf"
                files[filename] = code
            elif code and not files:  # If no filename but we have code, assume main.tf
                files["main.tf"] = code
        
        # Method 2: Look for markdown bold/header patterns
        # Pattern: **main.tf** or # main.tf followed by code
        if not files or len(files) < 3:
            # Pattern for **filename** followed by code block or code
            # Handle both with and without code blocks
            bold_patterns = [
                r'\*\*(\w+\.tf)\*\*[:\s]*\n```(?:terraform|hcl)?\s*\n(.*?)```',  # With code block
                r'\*\*(\w+\.tf)\*\*[:\s]*\n(.*?)(?=\n\*\*\w+\.tf\*\*|$)',  # Without code block
            ]
            
            for bold_pattern in bold_patterns:
                matches = re.finditer(bold_pattern, text, re.DOTALL | re.IGNORECASE)
                
                for match in matches:
                    filename = match.group(1).lower()
                    code = match.group(2).strip() if len(match.groups()) > 1 else ""
                    
                    # Skip if code is just another header (e.g., "**outputs.tf**")
                    if re.match(r'^\*\*\w+\.tf\*\*$', code.strip()):
                        continue
                    
                    # Remove markdown code block markers if present
                    code = re.sub(r'^```.*?\n', '', code, flags=re.MULTILINE)
                    code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
                    code = re.sub(r'^\*\*.*?\*\*', '', code, flags=re.MULTILINE)  # Remove any remaining bold markers
                    code = re.sub(r'^\*\*', '', code, flags=re.MULTILINE)  # Remove leading **
                    code = re.sub(r'\*\*$', '', code, flags=re.MULTILINE)  # Remove trailing **
                    
                    # Final validation: must have actual code content
                    if code and len(code) > 20 and not code.startswith('**') and not re.match(r'^\*\*\w+\.tf\*\*', code):
                        files[filename] = code
                
                if len(files) >= 3:
                    break
        
        # Method 2b: Look for file headers followed by code
        # Pattern: "## main.tf", "main.tf:", or "File: main.tf" followed by code block or code
        if not files or len(files) < 3:
            # Pattern 1: ## filename or filename: followed by ```code block```
            file_header_with_block = r'(?:^|\n)(?:##?\s+)?(\w+\.tf)[:\s]*\n```(?:terraform|hcl)?\s*\n(.*?)```'
            matches = re.finditer(file_header_with_block, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                filename = match.group(1).lower()
                code = match.group(2).strip()
                
                if code and len(code) > 20:  # Substantial code
                    files[filename] = code
            
            # Pattern 2: ## filename or filename: followed by code (no code block markers)
            if len(files) < 3:
                file_header_pattern = r'(?:^|\n)(?:##?\s+)?(?:File:?\s*)?(\w+\.tf)[:\s]*\n(.*?)(?=\n(?:##?\s+)?(?:File:?\s*)?\w+\.tf|$)'
                matches = re.finditer(file_header_pattern, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    filename = match.group(1).lower()
                    code = match.group(2).strip()
                    
                    # Remove markdown code block markers if present
                    code = re.sub(r'^```.*?\n', '', code, flags=re.MULTILINE)
                    code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
                    
                    if code and len(code) > 20:  # Only if we have substantial code
                        files[filename] = code
        
        # Method 3: Split by common separators and look for file patterns
        if not files or len(files) < 3:
            # Try splitting by "---" or "===" or double newlines
            sections = re.split(r'\n(?:---|===|```)', text)
            
            for section in sections:
                # Look for filename in first line
                first_line = section.split('\n')[0] if section else ""
                filename_match = re.search(r'(\w+\.tf)', first_line, re.IGNORECASE)
                
                if filename_match:
                    filename = filename_match.group(1).lower()
                    # Get content after first line
                    code = '\n'.join(section.split('\n')[1:]).strip()
                    if code and len(code) > 10:
                        files[filename] = code
        
        # Method 4: If we found some files but not all, try to extract remaining from text
        required = ["main.tf", "variables.tf", "outputs.tf"]
        found = set(files.keys())
        missing = [f for f in required if f not in found]
        
        if missing:
            log_warn(f"Missing files after extraction: {missing}")
            log_warn(f"Found files: {list(files.keys())}")
            # Try to find them in the raw text
            for filename in missing:
                # Look for the filename followed by content
                pattern = rf'{re.escape(filename)}[:\s]*\n(.*?)(?=\n\w+\.tf|$)'
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    code = match.group(1).strip()
                    # Clean up markdown
                    code = re.sub(r'^```.*?\n', '', code, flags=re.MULTILINE)
                    code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
                    if code and len(code) > 10:
                        files[filename] = code
        
        log_info(f"Extracted {len(files)} files: {list(files.keys())}")
        return files
    
    def generate(self, prompt: str, task_id: str, save_raw_response: bool = True) -> Dict[str, str]:
        """Generate Terraform code from a prompt.
        
        Args:
            prompt: The prompt template
            task_id: Task identifier
            save_raw_response: Whether to save raw LLM response for debugging
            
        Returns:
            Dictionary mapping filename to code content
        """
        # Replace task_id placeholder if present
        prompt = prompt.replace("<task_id>", task_id)
        
        log_info("Sending prompt to LLM...")
        
        # Generate code using LLM
        response = self.llm_client.generate(
            prompt=prompt,
            temperature=0.0,  # Deterministic output
            max_tokens=16000,
            reasoning_tokens=10000,
        )
        
        log_info(f"Received LLM response ({len(response)} characters)")
        
        # Save raw response for debugging
        if save_raw_response:
            debug_dir = Path("debug") / task_id
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / f"llm_response_{task_id}.txt"
            with open(debug_file, 'w') as f:
                f.write("="*80 + "\n")
                f.write("PROMPT\n")
                f.write("="*80 + "\n")
                f.write(prompt)
                f.write("\n\n" + "="*80 + "\n")
                f.write("LLM RESPONSE\n")
                f.write("="*80 + "\n")
                f.write(response)
            log_info(f"Raw LLM response saved to: {debug_file}")
        
        # Extract code blocks
        files = self.extract_code_blocks(response)
        
        # Validate extracted files
        required_files = ["main.tf", "variables.tf", "outputs.tf"]
        missing = [f for f in required_files if f not in files]
        
        if missing:
            log_warn(f"Missing required files: {missing}")
            log_warn("Attempting to extract from raw response...")
            
            # Last resort: try to extract from raw response more aggressively
            for filename in missing:
                # Look for filename in various formats
                patterns = [
                    rf'{re.escape(filename)}[:\s]*\n(.*?)(?=\n(?:variables|outputs|main)\.tf|$)',
                    rf'#{re.escape(filename)}[:\s]*\n(.*?)(?=\n#\w+\.tf|$)',
                    rf'File:\s*{re.escape(filename)}[:\s]*\n(.*?)(?=\nFile:|$)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                    if match:
                        code = match.group(1).strip()
                        # Remove code block markers
                        code = re.sub(r'^```.*?\n', '', code, flags=re.MULTILINE)
                        code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
                        if code and len(code) > 20:  # Substantial code
                            files[filename] = code
                            log_info(f"Extracted {filename} using fallback method")
                            break
        
        # Validate extracted files - reject headers or placeholders
        for filename in list(files.keys()):
            content = files[filename]
            # Reject if it's just a header or placeholder
            if (len(content) < 50 or 
                re.match(r'^\*\*\w+\.tf\*\*$', content.strip()) or
                content.strip().startswith('#') and 'placeholder' in content.lower() or
                content.strip().startswith('#') and 'failed' in content.lower()):
                log_warn(f"Rejecting {filename}: appears to be header/placeholder only")
                del files[filename]
        
        # Final check: if still missing, create placeholders but log warning
        for filename in required_files:
            if filename not in files:
                log_error(f"Failed to extract {filename} - creating placeholder")
                files[filename] = f"# {filename}\n# Code generation failed - placeholder file\n# Check debug/{task_id}/llm_response_{task_id}.txt for raw LLM response"
        
        # Log summary
        for filename, content in files.items():
            log_info(f"{filename}: {len(content)} characters")
            if len(content) < 50:
                log_warn(f"WARNING: {filename} seems too short ({len(content)} chars)")
                # Show preview
                preview = content[:200].replace('\n', '\\n')
                log_warn(f"  Preview: {preview}")
        
        return files
    
    def save_files(self, files: Dict[str, str], output_dir: Path) -> None:
        """Save generated files to directory.
        
        Args:
            files: Dictionary mapping filename to code content
            output_dir: Directory to save files to
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, content in files.items():
            file_path = output_dir / filename
            with open(file_path, 'w') as f:
                f.write(content)

