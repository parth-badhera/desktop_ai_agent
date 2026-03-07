# Local AI Desktop Agent (Ollama + Playwright)

A high-performance, deterministic AI agent that controls your desktop browser using local LLMs. Built with an **Intent-Based Architecture** for maximum reliability.

## 🚀 Features
- **Local-First**: Powered by Ollama (Llama 3). Your data stays on your machine.
- **Intent-Based Automation**: Uses structured intents (e.g., `youtube_search`) instead of brittle selector guessing.
- **Page Stabilization**: Intelligent waiting for `networkidle` states to ensure 100% action success.
- **Self-Healing JSON**: Robust bracket-counting parser that ignores LLM conversational noise.
- **Profile Support**: Seamlessly switches between Chrome profiles.

## 🛠 Setup

### 1. Requirements
- **Ollama**: [Download and install](https://ollama.com/)
- **Python 3.10+**
- **Google Chrome**

### 2. Install Dependencies
```bash
# Create and activate venv
python -m venv venv
source venv/bin/activate

# Install requirements
pip install ollama playwright
playwright install chrome
```

### 3. Pull the Model
```bash
ollama pull llama3
```

## 🎮 Usage
Run the main loop:
```bash
python main.py
```

### Example Commands:
- "Open chrome"
- "Play 'Alone' song on youtube"
- "Search for latest AI news on Google"
- "Open amazon.in and search for mechanical keyboards"

## 🏗 Architecture
- `brain.py`: LLM reasoning & prompt engineering.
- `browser.py`: Playwright-based browser control & stabilization.
- `parser.py`: Multi-step execution loop & error handling.
- `tools.py`: High-level intent-based tool definitions.
