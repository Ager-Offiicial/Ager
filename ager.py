#!/usr/bin/env python3
import os
import sys
import argparse
import requests
import json
import re
import datetime
import subprocess
import platform
import time
import pathlib
import string
import glob
from typing import Dict, List, Tuple, Optional, Any, Union

# Constants
VERSION = "0.3.2"
OLLAMA_API_BASE = "http://localhost:11434/api"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Add Git utilities class
class GitUtils:
    """Git utilities for version control integration."""
    
    @staticmethod
    def is_git_repo():
        """Check if the current directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def has_uncommitted_changes():
        """Check if there are uncommitted changes in the repo."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    @staticmethod
    def commit_changes(files, message=None):
        """Commit changes to specified files with an optional message."""
        if not files:
            return False
            
        if not message:
            message = f"Ager: Updated {', '.join(os.path.basename(f) for f in files)}"
            
        try:
            # Add files to staging
            subprocess.run(
                ["git", "add"] + files,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", message],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            return True
        except Exception as e:
            print(colorize(f"Git commit failed: {str(e)}", Colors.YELLOW))
            return False

# Add Codebase Mapper class
class CodebaseMapper:
    """Maps and provides information about files in the codebase."""
    
    def __init__(self, root_dir='.'):
        self.root_dir = root_dir
        self.file_cache = {}
        self.ignored_patterns = self._get_gitignore_patterns()
        
    def _get_gitignore_patterns(self):
        """Get patterns from .gitignore if it exists."""
        patterns = []
        gitignore_path = os.path.join(self.root_dir, '.gitignore')
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
                        
        # Add common patterns to ignore
        common_ignores = [
            '__pycache__', '*.pyc', '*.pyo', 
            'node_modules', '.git', '.vscode',
            '*.log', '*.tmp', 'dist', 'build'
        ]
        
        for pattern in common_ignores:
            if pattern not in patterns:
                patterns.append(pattern)
                
        return patterns
        
    def is_ignored(self, path):
        """Check if a path matches any ignored pattern."""
        rel_path = os.path.relpath(path, self.root_dir)
        
        for pattern in self.ignored_patterns:
            # Simple pattern matching (could be enhanced with proper gitignore rules)
            if pattern.startswith('*'):
                if rel_path.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if rel_path.startswith(pattern[:-1]):
                    return True
            elif pattern in rel_path:
                return True
                
        return False
        
    def scan_codebase(self, extensions=None):
        """Scan the codebase for files with optional extension filtering."""
        file_count = 0
        self.file_cache = {}
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip ignored files
                if self.is_ignored(file_path):
                    continue
                    
                # Filter by extension if specified
                if extensions and not any(file.endswith(ext) for ext in extensions):
                    continue
                    
                # Store relative path for better display
                rel_path = os.path.relpath(file_path, self.root_dir)
                self.file_cache[rel_path] = file_path
                file_count += 1
                
        return file_count
        
    def get_file_content(self, file_path):
        """Get the content of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding if utf-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except:
                return None
        except:
            return None
            
    def find_similar_files(self, name_pattern, limit=5):
        """Find files with similar names to the pattern."""
        matches = []
        
        for rel_path in self.file_cache:
            if name_pattern.lower() in rel_path.lower():
                matches.append(rel_path)
                
        return sorted(matches)[:limit]
        
    def get_relevant_files(self, query, limit=5):
        """Find files relevant to a query based on filename and content."""
        # Simple relevance scoring - could be enhanced with embeddings
        scores = {}
        
        query_terms = query.lower().split()
        
        for rel_path, abs_path in self.file_cache.items():
            # Score based on filename match
            filename_score = sum(term in rel_path.lower() for term in query_terms)
            
            # Skip content search if filename is not relevant at all
            if filename_score == 0 and len(query_terms) > 1:
                continue
                
            # Get file content for additional scoring
            content = self.get_file_content(abs_path)
            if content:
                # Simple content match scoring
                content_score = sum(content.lower().count(term) for term in query_terms)
                total_score = filename_score * 3 + min(content_score, 10)  # Cap content score
                
                if total_score > 0:
                    scores[rel_path] = total_score
        
        # Return top scoring files
        return [path for path, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]]

def colorize(text, color):
    """Add color to terminal text."""
    # Don't use colors on Windows unless using a compatible terminal
    if platform.system() == 'Windows' and 'TERM' not in os.environ:
        return text
    return f"{color}{text}{Colors.ENDC}"

def safe_api_call(url: str, method: str = "get", data: Dict = None, 
                  retries: int = MAX_RETRIES) -> Dict:
    """Make a safe API call with retries and proper error handling."""
    full_url = f"{OLLAMA_API_BASE}/{url.lstrip('/')}"
    
    for attempt in range(retries):
        try:
            if method.lower() == "get":
                response = requests.get(full_url)
            elif method.lower() == "post":
                response = requests.post(full_url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()  # Raise for 4xx/5xx status codes
            return response.json()
        
        except requests.exceptions.ConnectionError:
            if attempt == retries - 1:  # Last attempt
                raise ConnectionError("Cannot connect to Ollama. Make sure it's running.")
            print(colorize(f"Connection error, retrying in {RETRY_DELAY}s...", Colors.YELLOW))
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404 and "model not found" in e.response.text.lower():
                raise ValueError(f"Model not found. Please check available models with --list-models.")
            elif e.response.status_code == 500:
                raise RuntimeError(f"Ollama server error: {e.response.text}")
            else:
                raise
        
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(colorize(f"Error: {str(e)}, retrying in {RETRY_DELAY}s...", Colors.YELLOW))
            
        time.sleep(RETRY_DELAY)
    
    raise RuntimeError("Failed to make API call after multiple attempts")

def check_model_exists(model_name: str) -> bool:
    """Check if the specified model exists in Ollama."""
    try:
        models = safe_api_call("tags")
        return any(model.get("name") == model_name for model in models.get("models", []))
    except Exception as e:
        print(colorize(f"Error checking model: {str(e)}", Colors.RED))
        return False

def generate_response(model_name: str, prompt: str, temperature: float = 0.7, stream: bool = False):
    """Generate a response from the specified Ollama model.
    
    If stream is True, returns a generator that yields response chunks.
    Otherwise returns the complete response as a string.
    """
    request_data = {
        "model": model_name,
        "prompt": prompt,
        "stream": stream,
        "temperature": temperature,
        "num_predict": 2048  # More tokens for complex code generation
    }
    
    if stream:
        # Return a generator for streaming
        return stream_response(model_name, request_data)
    
    # Non-streaming response
    try:
        response = safe_api_call(
            "generate",
            method="post",
            data=request_data
        )
        return response.get("response", "No response generated")
    except ConnectionError as e:
        return f"Error: Cannot connect to Ollama. Make sure it's running. ({str(e)})"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def stream_response(model_name: str, request_data: Dict):
    """Stream a response from the Ollama API, yielding chunks as they arrive."""
    url = f"{OLLAMA_API_BASE}/generate"
    
    try:
        with requests.post(url, json=request_data, stream=True) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            yield data['response']
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"Streaming error: {str(e)}"

def chat_mode(model_name, temperature: float = 0.7, use_streaming: bool = True):
    """Start an interactive chat session with the model."""
    print(colorize(f"Starting chat with {model_name}" + 
                  (" (streaming enabled)" if use_streaming else ""), Colors.CYAN))
    print(colorize("Type 'exit' or 'quit' to end the session.", Colors.YELLOW))
    print(colorize("Type 'clear' to clear chat history.", Colors.YELLOW))
    print(colorize("Type 'save' to save the conversation.", Colors.YELLOW))
    print(colorize("Type 'help' to see available commands.", Colors.YELLOW))
    
    chat_history = []
    
    while True:
        user_input = input(colorize("\nYou: ", Colors.GREEN)).strip()
        
        # Handle special commands
        if user_input.lower() in ['exit', 'quit']:
            break
        elif user_input.lower() == 'clear':
            chat_history = []
            print(colorize("Chat history cleared.", Colors.YELLOW))
            continue
        elif user_input.lower() == 'save':
            # Save conversation to file
            filename = f"ager_chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Chat with {model_name} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for msg in chat_history:
                    f.write(f"{msg['role'].capitalize()}: {msg['content']}\n\n")
            print(colorize(f"Conversation saved to {filename}", Colors.GREEN))
            continue
        elif user_input.lower() == 'help':
            print(colorize("\nAvailable commands:", Colors.CYAN))
            print(colorize("  exit, quit - End the session", Colors.YELLOW))
            print(colorize("  clear - Clear chat history", Colors.YELLOW))
            print(colorize("  save - Save conversation to file", Colors.YELLOW))
            print(colorize("  help - Show this help message", Colors.YELLOW))
            continue
        elif not user_input:
            continue
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_input})
        
        # Prepare the prompt with chat history
        # Create a more structured prompt for better results
        system_message = "You are a helpful AI coding assistant. Be concise and focus on providing accurate and helpful responses."
        prompt = system_message + "\n\n"
        
        for msg in chat_history:
            prompt += f"{msg['role'].capitalize()}: {msg['content']}\n"
        
        prompt += "Assistant: "
        
        # Generate response
        if use_streaming:
            print(colorize("\nAger: ", Colors.CYAN), end="", flush=True)
            full_response = ""
            for chunk in generate_response(model_name, prompt, temperature, stream=True):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()  # Add a newline at the end
            response = full_response
        else:
            print(colorize("\nThinking...", Colors.BLUE))
            response = generate_response(model_name, prompt, temperature)
            print(colorize("\nAger: ", Colors.CYAN) + response)
        
        # Add assistant response to history
        chat_history.append({"role": "assistant", "content": response})

def extract_files_and_code(response):
    """Extract file names and code blocks from the LLM response."""
    files = []
    
    # Look for file listings first to help with context
    file_list_pattern = r"I'll create the following files:[\s\S]*?(?:```|<\/code>|$)"
    file_list_match = re.search(file_list_pattern, response)
    if file_list_match:
        file_list_text = file_list_match.group(0)
        file_patterns = re.findall(r'[-*]\s+`?([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)`?', file_list_text)
        expected_files = [sanitize_filename(f.strip()) for f in file_patterns if f.strip()]
    else:
        expected_files = []
    
    # Look for custom instructions
    custom_instruction_match = re.search(r'<custom_instructions>[\s\S]*?</custom_instructions>', response, re.IGNORECASE)
    custom_instructions = custom_instruction_match.group(0) if custom_instruction_match else ""
    combine_all_in_one = re.search(r'fit everything in a single html file', custom_instructions, re.IGNORECASE) is not None
    uk_english = re.search(r'respond in English \(UK\)', custom_instructions, re.IGNORECASE) is not None
    
    # Special case for handling a landing page or single file web page
    if re.search(r'(landing page|single file|webpage|web page|one file|website|saas)', response, re.IGNORECASE):
        # Check for custom instructions requesting single file HTML
        if not combine_all_in_one:
            combine_all_in_one = re.search(r'fit everything in a single html file', response, re.IGNORECASE) is not None
        
        # Try to find complete HTML blocks first
        html_matches = re.finditer(r'```(?:html\s+)?(?:[a-zA-Z0-9_\-\.\/\\]+\.html)?\n?(<!DOCTYPE\s+html>[\s\S]*?<\/html>)```|```html(?:\s+[a-zA-Z0-9_\-\.\/\\]+\.html)?\n([\s\S]*?)```', response, re.DOTALL | re.IGNORECASE)
        
        html_contents = []
        for html_match in html_matches:
            content = html_match.group(1) or html_match.group(2)
            if content and len(content.strip()) > 50:  # Only consider substantial content
                html_contents.append(content.strip())
        
        # Find a proper HTML document with doctype
        proper_html = None
        for content in html_contents:
            if re.search(r'<!DOCTYPE\s+html>', content, re.IGNORECASE):
                proper_html = content
                break
            
        # If no DOCTYPE is found, use the first substantial HTML content
        if not proper_html and html_contents:
            proper_html = html_contents[0]
            # Add DOCTYPE if missing
            if not re.search(r'<!DOCTYPE\s+html>', proper_html, re.IGNORECASE):
                proper_html = '<!DOCTYPE html>\n' + proper_html
        
        # If we found a proper HTML document, look for accompanying CSS and JS
        if proper_html:
            # Look for CSS content with a more robust pattern
            css_pattern = r'```(?:css\s+)?(?:[a-zA-Z0-9_\-\.\/\\]+\.css)?\n?([\s\S]*?(?:\}|\/\*[\s\S]*?\*\/))```'
            css_match = re.search(css_pattern, response, re.DOTALL | re.IGNORECASE)
            css_content = css_match.group(1).strip() if css_match else ""
            
            # Look for JS content with a more robust pattern
            js_pattern = r'```(?:(?:javascript|js)\s+)?(?:[a-zA-Z0-9_\-\.\/\\]+\.js)?\n?([\s\S]*?(?:function|\(\)|\{|\}|addEventListener))```'
            js_match = re.search(js_pattern, response, re.DOTALL | re.IGNORECASE)
            js_content = js_match.group(1).strip() if js_match else ""
            
            # Create a combined file if both HTML and (CSS or JS) are found
            if proper_html:
                # Check if HTML has head and body tags
                if "<head" not in proper_html:
                    if "<html" in proper_html:
                        proper_html = proper_html.replace("<html", "<html>\n<head>\n<title>Landing Page</title>\n</head>\n<body")
                    else:
                        proper_html = "<html>\n<head>\n<title>Landing Page</title>\n</head>\n<body>\n" + proper_html + "\n</body>\n</html>"
                
                if "</head>" not in proper_html and "<body" not in proper_html:
                    if "<title>" in proper_html:
                        proper_html = proper_html.replace("<title>", "<head>\n<title>")
                        proper_html = proper_html.replace("</title>", "</title>\n</head>\n<body>")
                    else:
                        # Add both head and body tags
                        proper_html = proper_html.replace("<html>", "<html>\n<head>\n<title>Landing Page</title>\n</head>\n<body>")
                
                # Check if CSS should be inline or in a style tag
                if "<style>" not in proper_html and css_content:
                    if "</head>" in proper_html:
                        proper_html = proper_html.replace("</head>", f"<style>\n{css_content}\n</style>\n</head>")
                    else:
                        # If no </head>, try to add before <body>
                        if "<body" in proper_html:
                            proper_html = proper_html.replace("<body", f"<style>\n{css_content}\n</style>\n<body")
                        else:
                            # Add at the beginning of the document
                            proper_html = f"<style>\n{css_content}\n</style>\n{proper_html}"
                
                # Check if CSS is linked externally and should be included
                external_css = re.search(r'<link[^>]*href=[\'"]([^\'"]*\.css)[\'"]', proper_html)
                if external_css and css_content and not combine_all_in_one:
                    # Create the CSS file separately
                    css_filename = external_css.group(1)
                    files.append({"filename": css_filename, "code": css_content})
                elif external_css and css_content and combine_all_in_one:
                    # Replace the link with an inline style
                    link_tag = re.search(r'<link[^>]*href=[\'"][^\'"]*\.css[\'"][^>]*>', proper_html)
                    if link_tag:
                        proper_html = proper_html.replace(link_tag.group(0), f"<style>\n{css_content}\n</style>")
                
                # Check if JS should be inline or in a script tag
                if "<script>" not in proper_html and js_content:
                    if "</body>" in proper_html:
                        proper_html = proper_html.replace("</body>", f"<script>\n{js_content}\n</script>\n</body>")
                    else:
                        # If no </body>, add before </html>
                        if "</html>" in proper_html:
                            proper_html = proper_html.replace("</html>", f"<script>\n{js_content}\n</script>\n</html>")
                        else:
                            # Add at the end of the document
                            proper_html = f"{proper_html}\n<script>\n{js_content}\n</script>"
                
                # Check if JS is linked externally and should be included 
                external_js = re.search(r'<script[^>]*src=[\'"]([^\'"]*\.js)[\'"]', proper_html)
                if external_js and js_content and not combine_all_in_one:
                    # Create the JS file separately
                    js_filename = external_js.group(1)
                    files.append({"filename": js_filename, "code": js_content})
                elif external_js and js_content and combine_all_in_one:
                    # Replace the script src with inline script
                    script_tag = re.search(r'<script[^>]*src=[\'"][^\'"]*\.js[\'"][^>]*>(?:</script>)?', proper_html)
                    if script_tag:
                        proper_html = proper_html.replace(script_tag.group(0), f"<script>\n{js_content}\n</script>")
                
                # Make sure we have proper HTML structure
                if "<body>" not in proper_html and "<body " not in proper_html:
                    if "<html>" in proper_html:
                        proper_html = proper_html.replace("<html>", "<html>\n<body>")
                    else:
                        proper_html = f"<body>\n{proper_html}\n</body>"
                
                if "</body>" not in proper_html:
                    if "</html>" in proper_html:
                        proper_html = proper_html.replace("</html>", "</body>\n</html>")
                    else:
                        proper_html = f"{proper_html}\n</body>"
                
                if "</html>" not in proper_html:
                    proper_html = f"{proper_html}\n</html>"
                
                # Find a filename for the HTML
                html_filename = "index.html"
                if expected_files:
                    for fname in expected_files:
                        if fname.endswith('.html'):
                            html_filename = fname
                            break
                
                # If we're combining everything, ensure CSS and JS are inline
                if combine_all_in_one:
                    # Process any remaining external CSS
                    remaining_css_links = re.findall(r'<link[^>]*href=[\'"]([^\'"]*\.css)[\'"][^>]*>', proper_html)
                    for css_href in remaining_css_links:
                        # Look for this CSS content again in the response
                        css_filename_pattern = rf'```css\s+{re.escape(css_href)}\n([\s\S]*?)```'
                        css_content_match = re.search(css_filename_pattern, response, re.DOTALL)
                        if css_content_match:
                            css_content = css_content_match.group(1).strip()
                            link_tag = re.search(rf'<link[^>]*href=[\']{re.escape(css_href)}[\'"][^>]*>', proper_html)
                            if link_tag:
                                proper_html = proper_html.replace(link_tag.group(0), f"<style>\n{css_content}\n</style>")
                    
                    # Process any remaining external JS
                    remaining_js_links = re.findall(r'<script[^>]*src=[\'"]([^\'"]*\.js)[\'"][^>]*>', proper_html)
                    for js_src in remaining_js_links:
                        # Look for this JS content again in the response
                        js_filename_pattern = rf'```(?:js|javascript)\s+{re.escape(js_src)}\n([\s\S]*?)```'
                        js_content_match = re.search(js_filename_pattern, response, re.DOTALL)
                        if js_content_match:
                            js_content = js_content_match.group(1).strip()
                            script_tag = re.search(rf'<script[^>]*src=[\']{re.escape(js_src)}[\'"][^>]*>(?:</script>)?', proper_html)
                            if script_tag:
                                proper_html = proper_html.replace(script_tag.group(0), f"<script>\n{js_content}\n</script>")
                
                files.append({"filename": html_filename, "code": proper_html})
                
                # If we created a combined HTML file with everything, return it
                if combine_all_in_one or ("style>" in proper_html and "script>" in proper_html):
                    # If we have only the HTML file, return just that
                    if all(f['filename'].endswith('.html') for f in files):
                        return files
                    # If we're explicitly asked to combine, filter out CSS/JS files
                    if combine_all_in_one:
                        files = [f for f in files if f['filename'].endswith('.html')]
                        return files
        
        # If we couldn't find a proper HTML document, build one from fragments
        if not proper_html:
            # This will be handled by our fallback extraction below
            pass
    
    # Enhanced regex pattern for code blocks
    # This pattern handles various markdown code block formats
    patterns = [
        # Standard markdown pattern with language and/or filename
        r'```(?:([\w\+]+)(?:\s+)?([\w\./\\-]+)?|(?:[\w\+]+\s+)?([\w\./\\-]+)?)\n(.*?)```',
        
        # Fallback pattern for simpler code blocks without language/filename
        r'```\n(.*?)```'
    ]
    
    # Try each pattern
    for pattern in patterns:
        matches = re.finditer(pattern, response, re.DOTALL)
        
        for match in matches:
            if len(match.groups()) >= 4:  # First pattern with language and filename
                language = match.group(1)
                filename1 = match.group(2)  # From first capture group format
                filename2 = match.group(3)  # From second capture group format
                code = match.group(4)
                filename = filename1 or filename2
            else:  # Second pattern (fallback) with just code
                language = None
                filename = None
                code = match.group(1)
            
            # Skip if we don't have any code content
            if not code:
                continue
                
            # Check if this is just instructions or examples rather than actual code
            if code and (
                "your code here" in code.lower() or 
                "html content here" in code.lower() or 
                "css code here" in code.lower() or 
                "javascript code here" in code.lower()
            ):
                continue
            
            # If filename is None but language might be a filename
            if not filename and language and '.' in language:
                filename = language
                language = None
            
            # If no filename was specified inside the code block, try to detect from context
            if not filename:
                # If we have expected files list, try to match the correct one based on language or content
                if expected_files and language:
                    for fname in expected_files:
                        ext = os.path.splitext(fname)[1].lower()
                        if (language.lower() == 'html' and ext == '.html') or \
                           (language.lower() in ['css', 'stylesheet', 'style'] and ext == '.css') or \
                           (language.lower() in ['js', 'javascript'] and ext == '.js') or \
                           (language.lower() in ['py', 'python'] and ext == '.py'):
                            filename = fname
                            break
                
                if not filename:
                    # Look for filename patterns before code blocks
                    context_before = response[:match.start()]
                    # Expanded pattern to catch more filename references
                    filename_patterns = [
                        r'(?:file(?:name)?s?|create|save|in|as|write to|named?|called|implement)[:\s]+[\'"`]?([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[\'"`]?',
                        r'[Ii]n\s+(?:a\s+)?(?:file(?:name)?|script|code|document)?\s+[\'"`]?([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[\'"`]?',
                        r'(?:file(?:name)?|script|code|document):\s*[\'"`]?([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)[\'"`]?',
                        r'(?:^|\n)([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+):',  # Filename at beginning of line followed by colon
                        r'[\-\*]\s+([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]+)'   # Filename in a list with dash or bullet
                    ]
                    
                    for pattern in filename_patterns:
                        filename_match = re.search(pattern, context_before)
                        if filename_match:
                            filename = filename_match.group(1)
                            break
            
            if not filename and language:
                # Try to determine filename from language
                ext_map = {
                    'python': '.py', 'py': '.py',
                    'javascript': '.js', 'js': '.js',
                    'typescript': '.ts', 'ts': '.ts',
                    'html': '.html', 'css': '.css',
                    'java': '.java', 'c': '.c', 'cpp': '.cpp',
                    'csharp': '.cs', 'cs': '.cs',
                    'rust': '.rs', 'go': '.go',
                    'ruby': '.rb', 'php': '.php',
                    'shell': '.sh', 'bash': '.sh',
                    'sql': '.sql'
                }
                
                if language and language.lower() in ext_map:
                    # Try to find a name for the file in context
                    name_match = re.search(r'(?:create|implement|write)[:\s]+(?:a|an)\s+([a-zA-Z0-9_\-]+)', response)
                    if name_match:
                        base_name = name_match.group(1)
                        filename = f"{base_name}{ext_map[language.lower()]}"
                    else:
                        # Use default names based on language
                        defaults = {
                            'html': 'index.html',
                            'css': 'styles.css',
                            'js': 'script.js',
                            'javascript': 'script.js',
                            'python': 'main.py',
                            'py': 'main.py'
                        }
                        filename = defaults.get(language.lower(), f"file{ext_map[language.lower()]}")
            
            # Use a generic filename if we still don't have one
            if not filename and code:
                # Try to guess language from code content
                if re.search(r'<html|<!DOCTYPE|<head|<body', code, re.IGNORECASE):
                    filename = 'index.html'
                elif re.search(r'function\s+\w+\s*\(|\bconst\b|\blet\b|\bvar\b|\bdocument\.', code):
                    filename = 'script.js'
                elif re.search(r'body\s*{|\.[\w-]+\s*{|\#[\w-]+\s*{', code):
                    filename = 'styles.css'
                elif re.search(r'import\s+|def\s+\w+\s*\(|class\s+\w+\s*:', code):
                    filename = 'main.py'
                else:
                    filename = 'file.txt'
            
            if filename and code:
                # Clean the code (remove extra newlines at beginning and end)
                code = code.strip()
                
                # Skip entries that look like examples rather than real code
                if "your code here" in code.lower() or code.count('\n') < 3 and len(code) < 50:
                    continue
                
                # Check if we already have this filename to avoid duplicates
                file_exists = any(f['filename'] == filename for f in files)
                if file_exists:
                    # Check if this is a duplicate with a numeric suffix
                    base_name, ext = os.path.splitext(filename)
                    if re.search(r'_\d+$', base_name):
                        # If it's already a numbered duplicate, skip it
                        continue
                    
                    # Add a number to make the filename unique
                    counter = 1
                    while any(f['filename'] == f"{base_name}_{counter}{ext}" for f in files):
                        counter += 1
                    filename = f"{base_name}_{counter}{ext}"
                
                # Check for duplicate content
                duplicate_content = False
                for existing_file in files:
                    if existing_file['code'] == code:
                        duplicate_content = True
                        break
                
                # Only add if not a duplicate and the code looks substantial
                if not duplicate_content and len(code) > 20:  # Skip very short code snippets
                    files.append({"filename": filename, "code": code})
    
    # If we don't have any CSS or JS files but have HTML, check if we need to extract them
    html_files = [f for f in files if f['filename'].endswith('.html')]
    css_files = [f for f in files if f['filename'].endswith('.css')]
    js_files = [f for f in files if f['filename'].endswith('.js')]
    
    # Check for custom instructions requesting single file HTML
    custom_instruction_match = re.search(r'fit everything in a single html file', response, re.IGNORECASE)
    combine_all_in_one = True if custom_instruction_match else False
    
    if html_files and not (css_files and js_files) and not combine_all_in_one:
        # We have HTML but no CSS or JS - let's see if we should extract them
        html_file = html_files[0]
        html_content = html_file['code']
        
        # Check for external CSS references
        css_refs = re.findall(r'<link[^>]*href=[\'"]([^\'"]*\.css)[\'"]', html_content)
        for css_ref in css_refs:
            # Look for CSS content in the response
            css_pattern = r'```(?:css\s+)?(?:[a-zA-Z0-9_\-\.\/\\]+\.css)?\n?([\s\S]*?(?:\}|\/\*[\s\S]*?\*\/))```'
            css_match = re.search(css_pattern, response, re.DOTALL | re.IGNORECASE)
            if css_match:
                css_content = css_match.group(1).strip()
                files.append({"filename": css_ref, "code": css_content})
        
        # Check for external JS references
        js_refs = re.findall(r'<script[^>]*src=[\'"]([^\'"]*\.js)[\'"]', html_content)
        for js_ref in js_refs:
            # Look for JS content in the response
            js_pattern = r'```(?:(?:javascript|js)\s+)?(?:[a-zA-Z0-9_\-\.\/\\]+\.js)?\n?([\s\S]*?(?:function|\(\)|\{|\}|addEventListener))```'
            js_match = re.search(js_pattern, response, re.DOTALL | re.IGNORECASE)
            if js_match:
                js_content = js_match.group(1).strip()
                files.append({"filename": js_ref, "code": js_content})
    elif html_files and (css_files or js_files) and combine_all_in_one:
        # We have separate files but need to combine them
        html_file = html_files[0]
        html_content = html_file['code']
        
        # Combine CSS files into the HTML
        for css_file in css_files:
            css_content = css_file['code']
            css_filename = css_file['filename']
            
            # Check if this CSS is already linked
            css_link = re.search(rf'<link[^>]*href=[\'"](?:[^\'"]*{re.escape(css_filename)}|{re.escape(css_filename)})[\'"][^>]*>', html_content)
            if css_link:
                # Replace the link with inline style
                html_content = html_content.replace(css_link.group(0), f"<style>\n{css_content}\n</style>")
            else:
                # Add as a new style tag before </head>
                if "</head>" in html_content:
                    html_content = html_content.replace("</head>", f"<style>\n{css_content}\n</style>\n</head>")
                else:
                    # Try to add before <body> if no head closing tag
                    html_content = re.sub(r'(<body[^>]*>)', f"<style>\n{css_content}\n</style>\n\\1", html_content)
        
        # Combine JS files into the HTML
        for js_file in js_files:
            js_content = js_file['code']
            js_filename = js_file['filename']
            
            # Check if this JS is already linked
            js_link = re.search(rf'<script[^>]*src=[\'"](?:[^\'"]*{re.escape(js_filename)}|{re.escape(js_filename)})[\'"][^>]*>(?:</script>)?', html_content)
            if js_link:
                # Replace the script tag with inline script
                html_content = html_content.replace(js_link.group(0), f"<script>\n{js_content}\n</script>")
            else:
                # Add as a new script tag before </body>
                if "</body>" in html_content:
                    html_content = html_content.replace("</body>", f"<script>\n{js_content}\n</script>\n</body>")
                else:
                    # Try to add before </html> if no body closing tag
                    html_content = html_content.replace("</html>", f"<script>\n{js_content}\n</script>\n</html>")
        
        # Update the HTML file content and remove CSS/JS files
        html_file['code'] = html_content
        files = [html_file]  # Keep only the combined HTML
    
    # If still no files detected, try fallback approaches
    if not files:
        return _extract_files_fallback(response)
    
    return files

def _extract_files_fallback(response):
    """Fallback method to extract files when standard pattern matching fails."""
    files = []
    
    # Special case - try to detect HTML content specifically for landing pages
    if re.search(r'(landing page|website|web page|html|css|javascript|js)', response, re.IGNORECASE):
        # Extract HTML content - be very permissive
        html_pattern = r'<!DOCTYPE\s+html>[\s\S]*?<html[\s\S]*?<\/html>'
        html_match = re.search(html_pattern, response)
        
        if html_match:
            content = html_match.group(0)
            # Check if this seems like a complete HTML file
            if "<head" in content and "<body" in content:
                files.append({"filename": "index.html", "code": content.strip()})
                return files
        
        # Try to build a complete HTML file from fragments
        head_tag = re.search(r'<head>[\s\S]*?<\/head>', response)
        body_tag = re.search(r'<body>[\s\S]*?<\/body>', response)
        style_tag = re.search(r'<style>[\s\S]*?<\/style>', response)
        script_tag = re.search(r'<script>[\s\S]*?<\/script>', response)
        
        # Extract individual HTML elements if no complete structure
        if not head_tag and not body_tag:
            html_elements = re.findall(r'<(?:div|section|nav|header|footer|h1|h2|p|ul|ol|form)[\s\S]*?<\/(?:div|section|nav|header|footer|h1|h2|p|ul|ol|form)>', response)
            if html_elements:
                body_content = "\n".join(html_elements)
            else:
                body_content = "<h1>Generated Landing Page</h1>\n<p>Content extracted from the response.</p>"
        else:
            body_content = body_tag.group(0) if body_tag else "<h1>Generated Landing Page</h1>\n<p>Content extracted from the response.</p>"
        
        # Extract CSS if available but no style tag found
        if not style_tag:
            css_blocks = re.findall(r'([.#]?[\w-]+\s*{[\s\S]*?})', response)
            if css_blocks:
                style_content = "<style>\n" + "\n".join(css_blocks) + "\n</style>"
            else:
                style_content = ""
        else:
            style_content = style_tag.group(0)
        
        # Extract JS if available but no script tag found
        if not script_tag:
            js_funcs = re.findall(r'(function\s+[\w$]+\s*\([\s\S]*?\)\s*{[\s\S]*?})', response)
            if js_funcs:
                script_content = "<script>\n" + "\n".join(js_funcs) + "\n</script>"
            else:
                script_content = ""
        else:
            script_content = script_tag.group(0)
        
        if body_content or style_content or script_content:
            html_template = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landing Page</title>
    {style}
</head>
<body>
    {body}
    {script}
</body>
</html>"""
            
            # Remove tags if they're included in the content
            body_content = re.sub(r'<\/?body>', '', body_content)
            
            # Set lang attribute based on detected language preference
            lang = "en-GB" if uk_english else "en"
            
            # Construct the HTML
            html_content = html_template.format(
                lang=lang,
                style=style_content,
                body=body_content,
                script=script_content
            )
            
            files.append({"filename": "index.html", "code": html_content})
            return files
    
    # Look for specific content patterns for common file types
    patterns = {
        'index.html': r'<!DOCTYPE html>[\s\S]*?<html[\s\S]*?<\/html>|<html[\s\S]*?<\/html>',
        'style.css': r'(?:\/\*[\s\S]*?\*\/|body\s*{[\s\S]*?}|\.[\w-]+\s*{[\s\S]*?})',
        'script.js': r'function\s+[\w$]+\s*\([\s\S]*?\)\s*{[\s\S]*?}|const\s+[\w$]+\s*=|let\s+[\w$]+\s*=',
        'main.py': r'import\s+[\w.]+|def\s+\w+\s*\([\s\S]*?\):|class\s+\w+\s*:'
    }
    
    for filename, pattern in patterns.items():
        matches = re.finditer(pattern, response, re.DOTALL)
        for match in matches:
            content = match.group(0)
            if content and len(content) > 50:  # Only add if substantial content
                files.append({"filename": filename, "code": content.strip()})
    
    return files

def can_execute_file(filename):
    """Check if a file can be executed based on its extension."""
    executable_extensions = {
        '.py': ['python', ''],
        '.js': ['node', ''],
        '.ts': ['ts-node', ''],
        '.sh': ['sh', ''],
        '.bat': ['', ''],
        '.cmd': ['', ''],
        '.ps1': ['powershell', '-File'],
        '.rb': ['ruby', ''],
        '.php': ['php', ''],
        '.pl': ['perl', ''],
        '.R': ['Rscript', ''],
        '.java': ['java', ''],  # Note: requires compilation first
    }
    
    _, ext = os.path.splitext(filename)
    return ext.lower() in executable_extensions, executable_extensions.get(ext.lower(), ['', ''])

def run_file(filename, interpreter=None, args=None):
    """Run a file using an appropriate interpreter."""
    if not os.path.exists(filename):
        print(colorize(f"Error: File {filename} does not exist.", Colors.RED))
        return False
    
    is_executable, default_cmd = can_execute_file(filename)
    
    if not is_executable and not interpreter:
        print(colorize(f"Error: Don't know how to execute {filename}. Please specify an interpreter.", Colors.RED))
        return False
    
    # Special case for Java files - check if compilation is needed
    if filename.endswith('.java'):
        # Extract class name from file
        class_name = os.path.splitext(os.path.basename(filename))[0]
        
        # Check if .class file exists and is older than .java file
        class_file = os.path.join(os.path.dirname(filename), f"{class_name}.class")
        if not os.path.exists(class_file) or os.path.getmtime(class_file) < os.path.getmtime(filename):
            print(colorize(f"Compiling {filename}...", Colors.YELLOW))
            compile_cmd = ['javac', filename]
            try:
                result = subprocess.run(
                    compile_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                print(colorize("Compilation successful.", Colors.GREEN))
            except subprocess.CalledProcessError as e:
                print(colorize(f"Compilation failed: {e.stderr}", Colors.RED))
                return False
        
        # If compilation succeeded, run the class file
        cmd = ['java', class_name]
    else:
        # For other file types
        cmd = []
        if interpreter:
            cmd.append(interpreter)
        elif default_cmd[0]:
            cmd.append(default_cmd[0])
            if default_cmd[1]:
                cmd.append(default_cmd[1])
        
        cmd.append(filename)
    
    if args:
        cmd.extend(args.split())
    
    try:
        print(colorize(f"\nRunning: {' '.join(cmd)}", Colors.CYAN))
        print(colorize("-" * 40, Colors.YELLOW))
        
        # Run the process and stream output
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8'
        )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        print(colorize("-" * 40, Colors.YELLOW))
        
        if process.returncode == 0:
            print(colorize(f"Process completed successfully (exit code: 0)", Colors.GREEN))
            return True
        else:
            print(colorize(f"Process exited with code: {process.returncode}", Colors.RED))
            return False
    
    except Exception as e:
        print(colorize(f"Error executing {filename}: {str(e)}", Colors.RED))
        return False

def verify_model_response(response, requested_features=None):
    """Verify if the model response complies with requested features."""
    if requested_features is None:
        requested_features = {}
    
    issues = []
    
    # Check for UK English if requested
    if requested_features.get('uk_english', False):
        # Look for American spelling patterns
        us_spelling = re.search(r'\b(color|center|behavior|neighbor|analog|catalog|dialog|flavor|honor|humor|labor|rumor|organize|realize|specialize|analyze)\b', response, re.IGNORECASE)
        if us_spelling:
            issues.append(f"US English spelling '{us_spelling.group(0)}' detected while UK English was requested")
    
    # Check for single HTML file if requested
    if requested_features.get('single_html', False):
        html_count = len(re.findall(r'```html', response, re.IGNORECASE))
        css_count = len(re.findall(r'```css', response, re.IGNORECASE))
        js_count = len(re.findall(r'```js|```javascript', response, re.IGNORECASE))
        
        if html_count > 0 and (css_count > 0 or js_count > 0):
            issues.append("Multiple files detected when a single HTML file was requested")
    
    # Check for Python-only task
    if requested_features.get('python_only', False):
        css_count = len(re.findall(r'```css', response, re.IGNORECASE))
        js_count = len(re.findall(r'```js|```javascript', response, re.IGNORECASE))
        html_count = len(re.findall(r'```html', response, re.IGNORECASE))
        
        if css_count > 0 or js_count > 0 or html_count > 0:
            issues.append("Non-Python files detected in a Python-only request")
    
    # Check for file listing format
    if not re.search(r"I'll create the following files?:", response, re.IGNORECASE):
        issues.append("Missing file listing section")
    
    # Check for code blocks
    if not re.search(r'```\w+', response):
        issues.append("No properly formatted code blocks found")
    
    return issues

def deduplicate_files(files):
    """Remove duplicate files with the same content but different names."""
    unique_files = []
    seen_content = {}
    
    for file in files:
        content = file['code']
        filename = file['filename']
        
        # Check if we've seen this content before
        if content in seen_content:
            base_name, ext = os.path.splitext(filename)
            if base_name.endswith('_' + ''.join(c for c in base_name if c.isdigit())):
                # This is likely a duplicate with a numbered suffix
                print(colorize(f"Skipping duplicate file: {filename}", Colors.YELLOW))
                continue
        
        # Add to unique files
        unique_files.append(file)
        seen_content[content] = filename
    
    return unique_files

def agent_mode(model_name, temperature=0.7):
    """Start an agent session for coding tasks in an aider-like interactive mode."""
    print(colorize(f"\n{'='*50}\nWelcome to Ager Agent Mode!\n{'='*50}", Colors.HEADER))
    print(colorize(f"Model: {model_name}", Colors.CYAN))
    print(colorize("Type your coding task or question below.", Colors.YELLOW))
    print(colorize("Type 'help' for a list of commands. Type 'exit' to quit.", Colors.YELLOW))
    print(colorize("You'll see one change at a time. Let's get started!", Colors.GREEN))

    # Set up Git integration
    has_git = GitUtils.is_git_repo()
    if has_git:
        print(colorize("\u2714 Git repository detected. Changes can be automatically committed.", Colors.GREEN))
    else:
        print(colorize("\u26A0 No Git repository detected. Consider initializing one for version control.", Colors.YELLOW))

    # Set up codebase mapping
    mapper = CodebaseMapper()
    file_count = mapper.scan_codebase()
    print(colorize(f"\u25B6 Scanned codebase: {file_count} files indexed.", Colors.CYAN))

    system_prompt = """
You are a professional AI coding assistant specializing in generating high-quality, functional code.
You operate in an interactive mode similar to aider.

**IMPORTANT: Multi-file Project Instructions**
- When the user requests a project with multiple files (e.g., HTML, CSS, JS), output each file SEPARATELY using this pattern:

  Filename: <filename>
  ```<language>
  ...file content...
  ```

- For example, for a web project:
  Filename: index.html
  ```html
  ...
  ```
  Filename: styles.css
  ```css
  ...
  ```
  Filename: script.js
  ```javascript
  ...
  ```

- Do NOT include explanations, lists, or extra commentary—just the filename and code block for each file.
- Use the correct language tag in the code block (e.g., html, css, javascript, python, etc.).
- If you are unsure, ask clarifying questions before generating code.
- For code edits, show the specific changes you're making rather than complete file rewrites.
- Write clean, well-documented code with appropriate comments.
- Follow standard naming conventions and best practices for the language you're using.
"""

    # Initialize chat history with system message
    chat_history = [{"role": "system", "content": system_prompt}]
    context_files = {}

    # Track modified files for Git commits
    modified_files = []

    def print_help():
        print(colorize("\nAvailable commands:", Colors.CYAN))
        print(colorize("  exit, quit      - End the session", Colors.YELLOW))
        print(colorize("  clear           - Clear chat history", Colors.YELLOW))
        print(colorize("  help            - Show this help message", Colors.YELLOW))
        print(colorize("  files           - List indexed files in the codebase", Colors.YELLOW))
        print(colorize("  find [pattern]  - Find files matching pattern", Colors.YELLOW))
        print(colorize("  show [file]     - Show contents of a file", Colors.YELLOW))
        print(colorize("  commit          - Commit modified files to git", Colors.YELLOW))
        print(colorize("  rescan          - Rescan the codebase for files", Colors.YELLOW))
        print(colorize("  /add <file>     - Load file into context", Colors.YELLOW))

    while True:
        try:
            user_input = input(colorize("\nYou: ", Colors.GREEN)).strip()
        except (EOFError, KeyboardInterrupt):
            print(colorize("\nSession interrupted. Exiting agent mode.", Colors.RED))
            break

        # Handle special commands
        if user_input.lower() in ['exit', 'quit']:
            # Offer to commit changes before exiting
            if has_git and modified_files and GitUtils.has_uncommitted_changes():
                commit_msg = input(colorize("Enter commit message (or press Enter for default): ", Colors.YELLOW))
                if GitUtils.commit_changes(modified_files, commit_msg if commit_msg else None):
                    print(colorize("Changes committed successfully.", Colors.GREEN))
            print(colorize("\nThank you for using Ager Agent Mode. Goodbye!\n", Colors.CYAN))
            break
        elif user_input.lower() == 'clear':
            chat_history = [{"role": "system", "content": system_prompt}]
            print(colorize("Chat history cleared.", Colors.YELLOW))
            continue
        elif user_input.lower() == 'help':
            print_help()
            continue
        elif user_input.lower() == 'files':
            if len(mapper.file_cache) > 0:
                print(colorize("\nIndexed files (showing first 20):", Colors.CYAN))
                for i, file in enumerate(sorted(mapper.file_cache.keys())[:20]):
                    print(colorize(f"  {file}", Colors.YELLOW))
                if len(mapper.file_cache) > 20:
                    print(colorize(f"  ...and {len(mapper.file_cache) - 20} more files", Colors.YELLOW))
            else:
                print(colorize("No files indexed. Run 'rescan' to index files.", Colors.YELLOW))
            continue
        elif user_input.lower() == 'rescan':
            file_count = mapper.scan_codebase()
            print(colorize(f"Rescanned codebase: {file_count} files indexed.", Colors.CYAN))
            continue
        elif user_input.lower() == 'commit':
            if has_git and modified_files:
                commit_msg = input(colorize("Enter commit message (or press Enter for default): ", Colors.YELLOW))
                if GitUtils.commit_changes(modified_files, commit_msg if commit_msg else None):
                    print(colorize("Changes committed successfully.", Colors.GREEN))
                    modified_files = []
                else:
                    print(colorize("Failed to commit changes.", Colors.RED))
            else:
                print(colorize("No changes to commit or Git not available.", Colors.YELLOW))
            continue
        elif user_input.lower().startswith('find '):
            pattern = user_input[5:].strip()
            if pattern:
                matches = mapper.find_similar_files(pattern)
                if matches:
                    print(colorize(f"\nFiles matching '{pattern}':", Colors.CYAN))
                    for file in matches:
                        print(colorize(f"  {file}", Colors.YELLOW))
                else:
                    print(colorize(f"No files found matching '{pattern}'", Colors.YELLOW))
            else:
                print(colorize("Please specify a pattern to search for.", Colors.YELLOW))
            continue
        elif user_input.lower().startswith('show '):
            filename = user_input[5:].strip()
            if filename:
                # Try exact match first, then fuzzy match
                content = None
                if filename in mapper.file_cache:
                    content = mapper.get_file_content(mapper.file_cache[filename])
                else:
                    # Try to find similar files
                    matches = mapper.find_similar_files(filename, limit=1)
                    if matches:
                        filename = matches[0]
                        content = mapper.get_file_content(mapper.file_cache[filename])
                if content:
                    print(colorize(f"\nContents of {filename}:", Colors.CYAN))
                    print(colorize("-" * 40, Colors.YELLOW))
                    print(content)
                    print(colorize("-" * 40, Colors.YELLOW))
                else:
                    print(colorize(f"File not found or unable to read: {filename}", Colors.RED))
            else:
                print(colorize("Please specify a file to show.", Colors.YELLOW))
            continue
        elif user_input.startswith("/add "):
            for file in user_input.split()[1:]:
                rel = file
                if rel in mapper.file_cache:
                    abs_path = mapper.file_cache[rel]
                elif os.path.exists(file):
                    abs_path = file
                    rel = os.path.relpath(file)
                else:
                    print(colorize(f"File not found: {file}", Colors.RED))
                    continue
                content = mapper.get_file_content(abs_path)
                if content is not None:
                    context_files[rel] = content
                    chat_history.append({"role": "system", "content": f"File: {rel}\n```\n{content}\n```"})
                    print(colorize(f"Added {rel} to context.", Colors.GREEN))
                else:
                    print(colorize(f"Unable to read {rel}", Colors.RED))
            continue
        elif not user_input:
            continue
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_input})
        
        # Find relevant files for context based on user query
        relevant_files = []
        if len(user_input) > 5:  # Only search for relevant files if query is substantial
            try:
                relevant_files = mapper.get_relevant_files(user_input)
            except Exception as e:
                print(colorize(f"Error finding relevant files: {e}", Colors.RED))
                relevant_files = []
            if relevant_files:
                context_files = {}
                context_content = "I've identified these relevant files in your codebase:\n\n"
                for rel_path in relevant_files:
                    abs_path = mapper.file_cache[rel_path]
                    try:
                        content = mapper.get_file_content(abs_path)
                    except Exception as e:
                        content = None
                        print(colorize(f"Error reading file {abs_path}: {e}", Colors.RED))
                    if content and len(content) < 10000:  # Limit to reasonably sized files
                        context_files[rel_path] = content
                        context_content += f"File: {rel_path}\n```\n{content}\n```\n"
                if context_content:
                    # Add top 2 most relevant files as context
                    chat_history.append({"role": "system", "content": context_content})

        # Prepare the prompt with chat history
        prompt = ""
        for msg in chat_history:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"{content}\n\n"
            else:
                prompt += f"{role.capitalize()}: {content}\n"
        prompt += "Assistant: "
        
        # Stream assistant response
        print(colorize("\nAger: ", Colors.CYAN), end="", flush=True)
        full_response = ""
        try:
            for chunk in generate_response(model_name, prompt, temperature, stream=True):
                print(chunk, end="", flush=True)
                full_response += chunk
        except Exception as e:
            print(colorize(f"Error generating response: {e}", Colors.RED))
            continue
        print()
        response = full_response
        
        # Add assistant response to history
        chat_history.append({"role": "assistant", "content": response})

        # Remove file context to keep history clean for future requests
        chat_history = [msg for msg in chat_history if not (msg["role"] == "system" and "I've identified these relevant files" in msg["content"])]

        # Look for code blocks that follow the expected pattern
        import re
        # Enhanced: extract multiple files from LLM response
        file_pattern = re.compile(
            r'Filename:\s*([\w\-\.\/\\]+)\s*```([a-zA-Z0-9_-]*)\s*([\s\S]*?)```',
            re.IGNORECASE
        )
        code_blocks = file_pattern.findall(response)
        # If no matches, fallback to any code block (default to python)
        if not code_blocks:
            fallback_blocks = re.findall(r'```([a-zA-Z0-9_-]*)\s*([\s\S]*?)```', response)
            code_blocks = [(f"untitled.{lang if lang else 'py'}", lang if lang else 'python', code) for lang, code in fallback_blocks]

        for i, block in enumerate(code_blocks):
            if len(block) == 3:
                filename, lang, code = block
            else:
                filename, lang, code = block[0], "python", block[1]  # fallback
            if not filename:
                filename = input(colorize("Enter filename for this code: ", Colors.GREEN)).strip()
                if not filename:
                    continue
            filename = sanitize_filename(filename)
            # Check if file already exists
            file_exists = os.path.exists(filename)
            if file_exists:
                old_content = open(filename, 'r', encoding='utf-8').read()
            else:
                directory = os.path.dirname(filename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                old_content = ''
            # Write new content
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)
            print(colorize(f"\nSaved: {filename}", Colors.GREEN))
            modified_files.append(filename)
            # Show diff if file existed
            if file_exists:
                print_diff(old_content, code)
            # Map markdown language to interpreter
            if input(colorize(f"Commit this change to Git? (y/n): ", Colors.YELLOW)).lower() == 'y':
                commit_msg = input(colorize("Enter commit message (or press Enter for default): ", Colors.YELLOW))
                if GitUtils.commit_changes([filename], commit_msg if commit_msg else None):
                    print(colorize("Change committed successfully.", Colors.GREEN))
                    modified_files.remove(filename)
                    rel_path = os.path.relpath(filename)
                    mapper.file_cache[rel_path] = filename
                    if has_git and GitUtils.has_uncommitted_changes():
                        if input(colorize("Commit this new file? (y/n): ", Colors.YELLOW)).lower() == 'y':
                            commit_msg = input(colorize("Enter commit message (or press Enter for default): ", Colors.YELLOW))
                            if GitUtils.commit_changes([filename], commit_msg if commit_msg else None):
                                print(colorize("File committed successfully.", Colors.GREEN))
                                modified_files.remove(filename)
        if modified_files:
            uncommitted = len(modified_files)
            if uncommitted > 0:
                print(colorize(f"\nYou have {uncommitted} uncommitted file changes. Type 'commit' to commit them.", Colors.YELLOW))
        print(colorize("\nWhat would you like to do next?", Colors.YELLOW))

def print_diff(old_content, new_content):
    """Print a polished, colorized diff between old and new content with line numbers."""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Header
    print(colorize("\n--- File Diff Preview ---", Colors.CYAN))
    max_len = max(len(old_lines), len(new_lines))
    width = len(str(max_len))

    # Show line-by-line diff
    for i in range(max_len):
        old = old_lines[i] if i < len(old_lines) else None
        new = new_lines[i] if i < len(new_lines) else None
        line_num = str(i+1).rjust(width)
        if old == new:
            print(f" {line_num}   {old if old is not None else ''}")
        elif old is None:
            print(colorize(f"+{line_num}   {new}", Colors.GREEN))
        elif new is None:
            print(colorize(f"-{line_num}   {old}", Colors.RED))
        else:
            print(colorize(f"-{line_num}   {old}", Colors.RED))
            print(colorize(f"+{line_num}   {new}", Colors.GREEN))
    print(colorize("--- End of Diff ---\n", Colors.CYAN))

def get_available_models():
    """Get a list of available models from Ollama."""
    try:
        response = safe_api_call("tags")
        return [model.get("name") for model in response.get("models", [])]
    except Exception as e:
        print(colorize(f"Error fetching models: {str(e)}", Colors.RED))
        return []

def print_banner(version=VERSION):
    """Print the Ager banner."""
    print(colorize("\n" + "="*60, Colors.CYAN))
    print(colorize("   █████╗  ██████╗ ███████╗██████╗", Colors.BLUE))
    print(colorize("  ██╔══██╗██╔════╝ ██╔════╝██╔══██╗", Colors.BLUE))
    print(colorize("  ███████║██║  ███╗█████╗  ██████╔╝", Colors.BLUE))
    print(colorize("  ██╔══██║██║   ██║██╔══╝  ██╔══██╗", Colors.BLUE))
    print(colorize("  ██║  ██║╚██████╔╝███████╗██║  ██║", Colors.BLUE))
    print(colorize("  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝", Colors.BLUE))
    print(colorize(f"  Agentic Coding Assistant v{version}", Colors.GREEN))
    print(colorize("="*60 + "\n", Colors.GREEN))

def check_ollama_status():
    """Check if Ollama is running and available."""
    try:
        safe_api_call("tags")
        return True
    except ConnectionError:
        print(colorize("Error: Cannot connect to Ollama. Make sure it's running.", Colors.RED))
        print(colorize("Visit https://ol  lama.ai/download to install Ollama.", Colors.YELLOW))
        return False
    except Exception as e:
        print(colorize(f"Error connecting to Ollama: {str(e)}", Colors.RED))
        return False

def sanitize_filename(filename):
    """Sanitize a filename to prevent path traversal and ensure valid characters."""
    # Get safe path by removing any path traversal
    safe_name = os.path.normpath(filename)
    if os.path.isabs(safe_name) or safe_name.startswith('..'):
        # If it's an absolute path or tries to go up, extract just the filename
        safe_name = os.path.basename(safe_name)
    
    # Replace any remaining invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    safe_name = ''.join(c if c in valid_chars else '_' for c in safe_name)
    
    # Ensure filename is not empty after sanitization
    if not safe_name or safe_name == '.':
        safe_name = "file.txt"
    
    return safe_name

def run_claude_agent(model_name, api_provider="anthropic"):
    pass  # Removed

def run_ager_pro_agent(model_name):
    pass  # Removed

def edit_mode(model_name, temperature: float = 0.7):
    """Interactive edit mode for existing files. Use /add to load files into context."""
    print(colorize("Entering edit mode...", Colors.CYAN))
    mapper = CodebaseMapper()
    context_files = {}
    edited_files = []
    has_git = GitUtils.is_git_repo()
    if has_git:
        print(colorize("Git repository detected: commits enabled.", Colors.GREEN))
    else:
        print(colorize("No Git repository detected: commit disabled.", Colors.YELLOW))
    print(colorize("Use /add <filename> to load files, /help for commands, /exit to quit.", Colors.YELLOW))
    while True:
        user_input = input(colorize("EditYou: ", Colors.GREEN)).strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            break
        if user_input.lower() == "/help":
            print(colorize("Commands:", Colors.CYAN))
            print(colorize("  /add <files> - Load files into context", Colors.YELLOW))
            print(colorize("  /list       - List loaded files", Colors.YELLOW))
            print(colorize("  /show <file> - Show file content", Colors.YELLOW))
            print(colorize("  /exit       - Exit edit mode", Colors.YELLOW))
            print(colorize("  /apply <file> - Apply LLM-generated edits", Colors.YELLOW))
            print(colorize("  /commit       - Commit edited files to Git", Colors.YELLOW))
            continue
        if user_input.startswith("/add "):
            for file in user_input.split()[1:]:
                filename = sanitize_filename(file)
                if os.path.exists(filename):
                    content = mapper.get_file_content(filename)
                    if content is not None:
                        context_files[filename] = content
                        print(colorize(f"Added {filename}", Colors.GREEN))
                    else:
                        print(colorize(f"Unable to read {filename}", Colors.RED))
                else:
                    print(colorize(f"File not found: {filename}", Colors.RED))
            continue
        if user_input.startswith("/list"):
            if context_files:
                print(colorize("Loaded files:", Colors.CYAN))
                for f in context_files:
                    print(colorize(f"  {f}", Colors.YELLOW))
            else:
                print(colorize("No files loaded.", Colors.YELLOW))
            continue
        if user_input.startswith("/show "):
            fname = user_input.split(maxsplit=1)[1]
            if fname in context_files:
                print(colorize(f"--- {fname} ---", Colors.CYAN))
                print(context_files[fname])
                print(colorize(f"--- End of {fname} ---", Colors.CYAN))
            else:
                print(colorize(f"{fname} not loaded.", Colors.RED))
            continue
        if user_input.startswith("/apply "):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print(colorize("Please specify a file to apply edits.", Colors.YELLOW))
                continue
            fname = parts[1]
            if fname not in context_files:
                print(colorize(f"File not loaded: {fname}", Colors.RED))
                continue
            old_content = context_files[fname]
            instructions = input(colorize("Edit instructions: ", Colors.YELLOW)).strip()
            if not instructions:
                print(colorize("No instructions provided.", Colors.YELLOW))
                continue
            edit_prompt = (
                f"You are an AI assistant. Apply the following edits to file {fname}."
                + "\nCurrent content:\n```python\n" + old_content + "\n```\n"
                + "Instructions:\n" + instructions + "\n"
                + "Provide only the full updated file content without explanations or commentary."
            )
            try:
                updated = generate_response(model_name, edit_prompt, temperature)
            except Exception as e:
                print(colorize(f"Error generating edit response: {e}", Colors.RED))
                continue
            # Extract code block if fences present
            match = re.search(r"```[a-zA-Z]*\n([\s\S]*)```", updated)
            new_content = match.group(1) if match else updated
            # Show diff and write changes
            print_diff(old_content, new_content)
            with open(fname, "w", encoding="utf-8") as fw:
                fw.write(new_content)
            context_files[fname] = new_content
            print(colorize(f"Applied edits to {fname}", Colors.GREEN))
            if fname not in edited_files:
                edited_files.append(fname)
            continue
        if user_input.startswith("/commit"):
            if not has_git:
                print(colorize("Git not available.", Colors.RED))
            elif not edited_files:
                print(colorize("No edits to commit.", Colors.YELLOW))
            else:
                msg = input(colorize("Enter commit message (or press Enter for default): ", Colors.YELLOW))
                if GitUtils.commit_changes(edited_files, msg if msg else None):
                    print(colorize("Changes committed.", Colors.GREEN))
                    edited_files.clear()
                else:
                    print(colorize("Commit failed.", Colors.RED))
            continue
        elif not user_input:
            continue
        
        # Build prompt with loaded files
        system_msg = "You are a helpful AI coding assistant. Focus on editing based on loaded files."
        prompt = system_msg + "\n\n"
        for fname, content in context_files.items():
            prompt += f"File: {fname}\n```python\n{content}\n```\n\n"
        prompt += f"User: {user_input}\nAssistant: "
        
        # Stream assistant response
        print(colorize("Ager: ", Colors.CYAN), end="", flush=True)
        full_response = ""
        for chunk in generate_response(model_name, prompt, temperature, stream=True):
            print(chunk, end="", flush=True)
            full_response += chunk
        print()
    print(colorize("Exiting edit mode.", Colors.CYAN))

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Ager - Agentic Coding Assistant")
    parser.add_argument("--model", type=str, help="Specify the model to use")
    parser.add_argument("--chat", action="store_true", help="Start a chat session")
    parser.add_argument("--agent", action="store_true", help="Start an agent session for coding tasks")
    parser.add_argument("--edit", action="store_true", help="Start edit mode for existing files")
    parser.add_argument("--list-models", action="store_true", help="List all available models")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--temperature", type=float, default=0.7, help="Set generation temperature (0.1-1.0)")
    parser.add_argument("--version", action="store_true", help="Display version information")
    args = parser.parse_args()
    
    # Handle version display
    if args.version:
        print(f"Ager version {VERSION}")
        sys.exit(0)
    
    # Disable colors if requested
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    # Print banner
    print_banner()
    
    # Check if Ollama is available
    try:
        check_ollama_status()
    except Exception as e:
        print(colorize(f"Warning: {str(e)}", Colors.YELLOW))
    
    # Get available models
    available_models = get_available_models()
    
    # Handle list models flag
    if args.list_models:
        print(colorize("Available models:", Colors.CYAN))
        for model in available_models:
            print(f"- {model}")
        sys.exit(0)
    
    # Select model
    model_name = args.model
    if not model_name and available_models:
        model_name = available_models[0]
        print(colorize(f"No model specified. Using: {model_name}", Colors.YELLOW))
    elif not model_name:
        print(colorize("Error: No model specified and no models available in Ollama.", Colors.RED))
        print(colorize("Please pull a model in Ollama first, for example:", Colors.YELLOW))
        print(colorize("  ollama pull llama2:7b", Colors.CYAN))
        sys.exit(1)
    
    # Use streaming by default unless disabled
    use_streaming = True
    
    # Set temperature within valid range
    temperature = max(0.1, min(1.0, args.temperature))
    
    # Handle different modes
    if args.chat:
        chat_mode(model_name, temperature, use_streaming)
    elif args.agent:
        agent_mode(model_name, temperature)
    elif args.edit:
        edit_mode(model_name, temperature)
    else:
        # Default to chat mode
        chat_mode(model_name, temperature, use_streaming)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colorize("\nExiting Ager. Goodbye!", Colors.CYAN))
    except Exception as e:
        print(colorize(f"\nError: {str(e)}", Colors.RED))
        print(colorize("If this problem persists, please report the issue.", Colors.YELLOW)) 