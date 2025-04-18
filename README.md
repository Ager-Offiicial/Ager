# Ager

An agentic coding assistant that works in your terminal using local LLMs from Ollama.

![Version](https://img.shields.io/badge/version-0.3.2-blue)

## What's New in v0.3.0


- **Local Model Support**: Use local Ollama models with advanced agents
- **Enhanced Tools**: More powerful code analysis and file operations
- **Improved UI**: Better terminal display with rich formatting

## Prerequisites

- Python 3.6+
- [Ollama](https://ollama.ai/) installed and running
- One or more language models pulled into Ollama (e.g., codellama:13b, mistral:7b, etc.)
- Works best with deepcoder:14b

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Ager-Offiicial/Ager/
   cd Ager
   ```

2. Choose one of the installation methods:

   **Option 1: Pip installation**
   ```
   pip install -e .
   ```
   
   **Option 2: Windows batch file**
   ```
   install.bat
   ```
   
   **Option 3: PowerShell users (recommended for PowerShell)**
   ```
   .\install_powershell.bat
   ```
   This creates a PowerShell module that allows you to use the `ager` command directly in PowerShell.

## Usage

### Basic Commands

```
ager --model MODEL_NAME --chat       # Start a chat session
ager --model MODEL_NAME --agent      # Start an agent for coding tasks
ager --model MODEL_NAME --edit       # Start an edit mode for reading and editing existing files
ager --list-models                   # Show available models
ager --no-color                      # Disable colored output
ager --help or -h                    # Show help information
```



### Chat Mode

Chat mode allows you to have a conversation with the LLM:

```
ager --model llama3.1:8b --chat
```

#### Chat Commands

While in chat mode, you can use these special commands:
- `exit` or `quit` - End the session
- `clear` - Clear chat history
- `save` - Save conversation to file
- `help` - Show available commands

### Agent Mode

Agent mode helps you generate code based on your requirements:

```
ager --model deepcoder:14b --agent
```

#### How Agent Mode Works

1. Describe what you want to build
2. The agent will generate code and list files it plans to create
3. You can view the full LLM response if needed
4. You'll be asked to confirm each file creation
5. The agent checks for existing files and handles directories automatically
6. After file creation, you can run executable files directly

### Edit Mode (in beta might not work properly)

Edit mode edits existing files of the selected codebase:

```
ager --model deepcoder:14b --edit
```

## Features

- Interactive chat interface with AI models
- Local file system access for reading and writing code
- creating and editing files
- Support for ollama



## Requirements

- Python 3.8 or higher
- Ollama (for local models)
- Google API key (for Gemini models)




## Troubleshooting

### Windows-specific Issues
- If you encounter `ModuleNotFoundError: No module named 'readline'`, run the Windows fix script as described above.

### Ollama Connection Issues
- Make sure Ollama is running locally at http://localhost:11434
- Check that the requested model is available in your Ollama installation


## Examples

### Listing Available Models

```
ager --list-models
```

### Starting Chat Mode

```
ager --model mistral:7b --chat
```

### Using Agent Mode to Create and Run a Python Script

```
ager --model deepcoder:14b --agent
```

Then describe your coding task when prompted, such as: "Create a simple weather API client in Python"



### Automatic Model Selection

If you don't specify a model, Ager will automatically use the first available model in your Ollama installation:

```
ager --chat
ager --agent
```

## License

MIT