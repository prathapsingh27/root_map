# AI Career Roadmap & Skill Gap Finder

A Streamlit application that uses Ollama and Gemma 4 to create:
- Skill gap analysis
- An eight-week learning roadmap
- Exactly three portfolio project suggestions
- Career readiness guidance

## Requirements

- Python 3.12 recommended
- Ollama installed and running
- Gemma model available to Ollama
- A reachable Ollama endpoint for cloud deployment

## Local setup (Windows PowerShell)

1. Install Python 3.12 and Ollama.
2. Download the model:

   ```powershell
   ollama pull gemma4:e4b
   ```

3. Create and activate a virtual environment:

   ```powershell
   py -3.12 -m venv venv
   .\venv\Scripts\activate
   ```

4. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and set your Ollama host.

6. Run the app:

   ```powershell
   streamlit run app.py
   ```

Open http://localhost:8501.

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Create an app at https://share.streamlit.io/.
3. Select the repository, branch, and `app.py`.
4. Set Python version to 3.12 if offered.
5. In Streamlit app settings, add secrets:

   ```toml
   [ollama]
   host = "https://YOUR-SECURE-OLLAMA-ENDPOINT"
   token = "YOUR_ACCESS_TOKEN"
   ```

6. Deploy.

## Important deployment note

Streamlit Community Cloud does not share your computer's localhost.
For a cloud deployment, Ollama must run on a separate server reachable
from the Streamlit app. Secure the endpoint with HTTPS and authentication.
Do not expose an unauthenticated Ollama service to the public internet.
Do not commit `.streamlit/secrets.toml`.

## Notes

- Generated reports are stored in Streamlit session state for the current session.
- Study hours are validated against the weekly limit supplied by the student.
- The app validates that the model returns eight weeks and three projects.
- AI-generated career guidance is an estimate, not a job-placement guarantee.
