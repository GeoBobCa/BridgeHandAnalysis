Markdown

# Bridge Master

Bridge Master is a Python application designed to generate, analyze, and teach Bridge hands. It uses Google's Gemini AI to provide "Audrey Grant-style" feedback on bidding, play, and educational takeaways.

## 📋 Prerequisites

* **Python 3.10+**
* **uv** (An extremely fast Python package manager)
    * *To install uv on Windows:* `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

## ⚙️ Installation

1.  **Clone or Download** this repository.
2.  **Open a Terminal** in the project folder.
3.  **Create the Virtual Environment:**
    ```bash
    uv venv
    ```
4.  **Activate the Environment:**
    * *Windows (PowerShell):*
        ```powershell
        .venv\Scripts\activate
        ```
5.  **Install Dependencies:**
    ```bash
    uv pip install -r requirements.txt
    ```

## 🔑 Configuration (The .env file)

You must create a file named `.env` in the root folder (next to `main.py`) to store your API key.

1.  Create a file named `.env`
2.  Add your Google Gemini API key:
    ```text
    GEMINI_API_KEY=AIzaSy...[Your Key Here]...
    ```
    *(Note: Do not use quotes or spaces around the key)*

## 🚀 How to Run

**Important:** Always run the application using the `python` command to ensure it uses the correct virtual environment libraries.

```bash
python main.py
📂 Project Structure
main.py: The entry point of the application.

src/core/: Backend logic (AI Orchestrator, Database handlers).

src/ui/: User Interface code (PySide6 / PyQt).

data/: Stores the local SQLite database (bridge_master.db).

docs/: Detailed documentation and troubleshooting guides.

🛠 Troubleshooting
If you encounter errors (API Quotas, Module Not Found, etc.), please consult docs/TROUBLESHOOTING.md for specific solutions.


---
