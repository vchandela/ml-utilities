from typing import List, Dict, Any
import os
import sys

from dotenv import load_dotenv
import openai

load_dotenv()

def create_assistant():
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please set OPENAI_API_KEY in your .env file")
        sys.exit(1)
    
    try:
        client = openai.Client()
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        print("Please check your OpenAI API key")
        sys.exit(1)

    functions: List[Dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "create_directory",
                "description": "Create a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the directory to be created",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_content_to_file",
                "description": "Save content (code or text) to file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content to save",
                        },
                        "path": {
                            "type": "string",
                            "description": "The path to the file, including extension",
                        },
                    },
                    "required": ["content", "path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the directory",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "commit",
                "description": "Commit changes to the repo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The commit message",
                        },
                    },
                    "required": ["message"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "make_pull_request",
                "description": "Creates a new branch and makes a pull request",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the pull request",
                        }
                    },
                    "required": ["title"],
                },
            },
        },
    ]

    try:
        ai_developer = client.beta.assistants.create(
                instructions="""You are an AI developer. You help user work on their tasks related to coding in their codebase. The provided codebase is in the /home/user/repo.
            When given a coding task, work on it until completion, commit it, and make pull request.

            If you encounter a problem, communicate it promptly, please.

            You can create and save content (text or code) to a specified file (or create a new file), list files in a given directory, read files, commit changes, and make pull requests. Always make sure to write the content in the codebase.

            By default, always either commit your changes or make a pull request after performing any action on the repo. This helps in reviewing and merging your changes.
            Name the PR based on the changes you made.

            Be professional, avoid arguments, and focus on completing the task.

            When you finish the task, always provide the link to the pull request you made (if you made one.)
            Additionally, be prepared for discussions; not everything user writes implies changes to the repo. For example, if the user writes "thank you", you can simply answer "you are welcome".
            But by default, if you are assigned a task, you should immediately do it in the provided repo, and not talk only talk about your plan.
            """,
                name="AI Developer",
                tools=functions,
                model="gpt-4-1106-preview",
            )

        print("AI Developer Assistant created, copy its id to .env file:")
        print(ai_developer.id)
    except Exception as e:
        print(f"Error creating assistant: {e}")
        print("Please check your OpenAI API key and try again")
        sys.exit(1)


if __name__ == "__main__":
    create_assistant()