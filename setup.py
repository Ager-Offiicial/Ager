from setuptools import setup, find_packages

setup(
    name="ager",
    version="0.3.0",
    description="An agentic coding assistant using local LLMs from Ollama",
    author="Ager Developer",
    packages=find_packages(),
    py_modules=["ager", "claude_agent", "ager_pro"],
    install_requires=[
        "requests>=2.25.0",
        "rich",
        "anthropic",
        "google-generativeai",
    ],
    entry_points={
        "console_scripts": [
            "ager=ager:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
) 