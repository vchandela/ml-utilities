## Reference
https://medium.com/e-two-b/i-built-an-ai-developer-that-makes-pull-requests-a51fa6bde412

## Steps to run
- Create a virtual environment
- Install dependencies: pip install -r requirements.txt
- Add `OPENAI_API_KEY` in `.env`
- Run: `python assistants.py` to create your assistant ID
- Copy the assistant ID to your `.env` file as `AI_ASSISTANT_ID`
- Add remaining keys in `.env`
- `python main.py`