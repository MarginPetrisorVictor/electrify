from setuptools import setup, find_packages

setup(
    name="electrify",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "typer",
        "rich",
        "langchain-google-genai",
        "langchain-core",
        "langgraph",
        "pymongo",
        "python-dotenv",
        "pathspec"
    ],
    entry_points={
        "console_scripts": [
            "arise = cli.main:app",
        ],
    },
)