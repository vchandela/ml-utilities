import os
import sys
from dotenv import load_dotenv
from e2b_code_interpreter.code_interpreter_sync import Sandbox
import openai
import time
import json

from rich import print
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt


class MyPrompt(Prompt):
    prompt_suffix = ""


custom_theme = Theme(
    {
        "theme": "bold #666666",
    }
)
console = Console(theme=custom_theme)

load_dotenv()
client = openai.Client()

AI_ASSISTANT_ID = os.getenv("AI_ASSISTANT_ID")
USER_GITHUB_TOKEN = os.getenv("USER_GITHUB_TOKEN")
E2B_API_KEY = os.getenv("E2B_API_KEY")

if not AI_ASSISTANT_ID:
    print("Error: AI_ASSISTANT_ID environment variable is not set")
    print("Please run 'python assistants.py' first to create an assistant, then add the ID to your .env file")
    sys.exit(1)

if not E2B_API_KEY:
    print("Error: E2B_API_KEY environment variable is not set")
    print("Please get your E2B API key from https://e2b.dev and add it to your .env file")
    sys.exit(1)

if not USER_GITHUB_TOKEN:
    print("Error: USER_GITHUB_TOKEN environment variable is not set")
    print("Please get your GitHub token from https://github.com/settings/tokens and add it to your .env file")
    sys.exit(1)

try:
    assistant = client.beta.assistants.retrieve(AI_ASSISTANT_ID)
except Exception as e:
    print(f"Error retrieving assistant: {e}")
    print("Please check your OpenAI API key and assistant ID")
    sys.exit(1)

def prompt_user_for_github_repo():
    user_repo = MyPrompt.ask(
        "\nWhat GitHub repo do you want to work in? Specify it like this: [bold #E0E0E0]your_username/your_repo_name[/bold #E0E0E0].\n> "
    )
    print("\n🔄[#666666] Setting up the environment...[/#666666]", end="\n")
    print("", end="\n")

    repo_url = f"https://github.com/{user_repo.strip()}.git"
    return repo_url

def prompt_user_for_task(repo_url):
    user_task_specification = MyPrompt.ask(
        "\n\n🤖[#E57B00][bold] The AI developer is ready to work[/bold][/#E57B00]\n\nWhat do you want to do?\n> "
    )
    user_task = (
        f"Please work with the GitHub repository {repo_url}. "
        f"Clone it to /tmp/repo, then: {user_task_specification}"
    )
    print("", end="\n")
    return user_task

def prompt_user_for_auth():
    user_auth = MyPrompt.ask(
        "\nProvide [bold]GitHub token[/bold] with following permissions:\n\n• read:org\n• read:project\n• repo\n\nFind or create your token at [bold #0096FF]https://github.com/settings/tokens[/bold #0096FF]\n\nToken:",
        password=True,
    )
    print("", end="\n")
    return user_auth

def execute_code_with_interpreter(code_interpreter, code):
    """Execute Python code in the E2B Code Interpreter"""
    print("🔄 [#666666]Executing code...[/#666666]")
    print(f"[dim]Code to execute:[/dim]\n{code[:200]}{'...' if len(code) > 200 else ''}\n")
    
    try:
        exec_result = code_interpreter.run_code(
            code,
            on_stderr=lambda stderr: print(f"[red][E2B Stderr][/red] {stderr}"),
            on_stdout=lambda stdout: print(f"[green][E2B Stdout][/green] {stdout}"),
        )
        
        if exec_result.error:
            print(f"[red]Error executing code:[/red] {exec_result.error}")
            return f"Error: {exec_result.error}"
        
        # Return the results
        results = []
        for result in exec_result.results:
            if hasattr(result, 'text'):
                results.append(result.text)
            elif hasattr(result, 'html'):
                results.append(result.html)
        
        return "\n".join(results) if results else "Code executed successfully"
        
    except Exception as e:
        error_msg = f"Error executing code: {str(e)}"
        print(f"[red]{error_msg}[/red]")
        return error_msg

def create_github_operations_code(repo_url, github_token, task):
    """Generate Python code for GitHub operations"""
    return f'''
import os
import subprocess
import sys

# Set up GitHub token
os.environ['GITHUB_TOKEN'] = '{github_token}'

def run_command(cmd, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            print(f"Error running command: {{cmd}}")
            print(f"Error: {{result.stderr}}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        print(f"Exception running command: {{cmd}}")
        print(f"Exception: {{str(e)}}")
        return False, str(e)

# Clone the repository
print("Cloning repository...")
success, output = run_command("rm -rf /tmp/repo")  # Clean up first
success, output = run_command("git clone {repo_url} /tmp/repo")
if not success:
    print("Failed to clone repository")
    print(output)
else:
    print("Repository cloned successfully")

# Set up git configuration
print("Setting up git configuration...")
run_command("git config --global user.email 'ai-developer@email.com'")
run_command("git config --global user.name 'AI Developer'")

# Install GitHub CLI first
print("Installing GitHub CLI...")
run_command("curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg")
run_command('echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null')
run_command("sudo apt update")
run_command("sudo apt install gh -y")

# Set up GitHub CLI authentication
print("Setting up GitHub authentication...")
print("GitHub CLI will use GITHUB_TOKEN environment variable for authentication")
# Test if GitHub CLI can access the repository
success, output = run_command("gh auth status")
if success:
    print("GitHub authentication successful")
    run_command("gh auth setup-git")
else:
    print("GitHub authentication test:")
    print(output)

# List the repository contents
print("Repository contents:")
success, output = run_command("ls -la", cwd="/tmp/repo")
if success:
    print(output)

print("Ready to work on the task: {task}")
print("Repository is available at /tmp/repo")
'''

def main():
    print("\n🤖[#E57B00][bold] AI GitHub Developer[/#E57B00][/bold]")
    print("\n✅ [#666666]GitHub token loaded[/#666666]\n")

    # Get repository and task from user
    repo_url = prompt_user_for_github_repo()
    
    # Create E2B Code Interpreter
    with Sandbox(api_key=E2B_API_KEY) as code_interpreter:
        print("✅ [#666666]Code interpreter initialized[/#666666]")
        
        # Set up the GitHub environment
        setup_code = create_github_operations_code(repo_url, USER_GITHUB_TOKEN, "Initial setup")
        execute_code_with_interpreter(code_interpreter, setup_code)
        
        while True:
            user_task = prompt_user_for_task(repo_url)
            
            # Create a thread with the OpenAI assistant
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are an AI developer working with a GitHub repository that has been cloned to /tmp/repo.

Available tools:
- The repository is already cloned at /tmp/repo
- GitHub CLI is authenticated and ready to use
- Git is configured with AI Developer credentials
- You can run any Python code to interact with files, git, and GitHub

Your task: {user_task}

Please write Python code to complete this task. You can:
1. Read and modify files in /tmp/repo
2. Use git commands (git add, git commit, git push, etc.)
3. Use GitHub CLI (gh pr create, etc.)
4. Run any shell commands using subprocess

Write the Python code to accomplish the task and make a pull request if appropriate.""",
                    },
                ],
            )

            run = client.beta.threads.runs.create(
                thread_id=thread.id, assistant_id=assistant.id
            )

            # Monitor the run
            spinner = ""
            with console.status(spinner):
                previous_status = None
                while True:
                    if run.status != previous_status:
                        console.print(
                            f"[bold #FF8800]>[/bold #FF8800] Assistant status: {run.status} [#666666](waiting for OpenAI)[/#666666]"
                        )
                        previous_status = run.status

                    if run.status == "completed":
                        console.print("\n✅[#666666] Run completed[/#666666]")
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        
                        # Get the latest assistant message
                        for message in messages.data:
                            if message.role == "assistant":
                                content = message.content[0].text.value
                                console.print("Assistant response:", content)
                                
                                # Extract and execute any Python code from the response
                                import re
                                code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
                                if not code_blocks:
                                    code_blocks = re.findall(r'```\n(.*?)\n```', content, re.DOTALL)
                                
                                for code_block in code_blocks:
                                    print("\n🔄 [#666666]Executing assistant's code...[/#666666]")
                                    result = execute_code_with_interpreter(code_interpreter, code_block)
                                    print(f"Result: {result}")
                                
                                break
                        break

                    elif run.status in ["queued", "in_progress"]:
                        pass

                    elif run.status in ["cancelled", "cancelling", "expired", "failed"]:
                        console.print(f"[red]Run failed with status: {run.status}[/red]")
                        break

                    else:
                        print(f"Unknown status: {run.status}")
                        break

                    run = client.beta.threads.runs.retrieve(
                        thread_id=thread.id, run_id=run.id
                    )
                    time.sleep(1)

if __name__ == "__main__":
    main()