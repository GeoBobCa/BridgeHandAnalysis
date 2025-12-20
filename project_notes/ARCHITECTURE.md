Here is the content for docs/ARCHITECTURE.md.

This document explains how your application is built. It is useful when you want to add new features (like a new AI persona or a different database) and need to remember how the pieces fit together.

File: docs/ARCHITECTURE.md
(Copy the content below into that file)

Markdown

# Bridge Master Architecture

This document outlines the technical design, module structure, and data flow of the Bridge Master application.

## 🏗 High-Level Overview

Bridge Master follows a modular **Model-View-Controller (MVC)** pattern:

* **View (UI):** Built with **PySide6** (Qt). Handles user inputs, displays card tables, and renders AI feedback.
* **Controller (Logic):** Python scripts in `src/core/` that manage the rules of Bridge, handle database connections, and format data for the AI.
* **Model (Data):**
    * **Local:** SQLite database (`bridge_master.db`) stores generated hands and history.
    * **Remote:** Google Gemini API provides analysis and educational commentary.

---

## 📂 System Modules

### 1. The User Interface (`src/ui/`)
* **`main_window.py`**: The application entry point. It initializes the GUI, connects buttons to functions, and manages the main event loop.
* **`hand_display.py`** (concept): Responsible for rendering the graphical representation of Bridge hands (North/South/East/West).

### 2. The Core Logic (`src/core/`)
* **`ai_orchestrator.py`**:
    * **Role:** The bridge between your local Python code and Google's servers.
    * **Key Library:** `google-genai` (Official Google v1 SDK).
    * **Function:** Accepts raw hand data, constructs the "Audrey Grant" system prompt, sends it to Gemini, and validates the JSON response.
* **`database.py`** (implied):
    * **Role:** Manages the SQLite connection.
    * **Key Function:** Saving generated hands so they can be reloaded later without re-generating.

---

## 🤖 The AI Analysis Pipeline

The most complex part of the system is how a Bridge hand is converted into educational feedback.

1.  **Data Collection:**
    * The app generates a hand and calculates "Ground Truth" math (HCP, distribution) using local Python logic. This ensures the AI doesn't have to do math (which LLMs are sometimes bad at).

2.  **Context Construction (`ai_orchestrator.py`):**
    * The raw data is packaged into a JSON payload.
    * A **System Prompt** is attached, defining the persona: *"You are the Audrey Grant Bridge Mentor."*

3.  **API Request:**
    * **SDK:** `google-genai`
    * **Model:** `gemini-flash-latest` (Selected for speed and free-tier availability).
    * **Transport:** Secure HTTPS call to Google Cloud.

4.  **Response Parsing:**
    * The AI returns a structured JSON object containing:
        * `bidding_critique`
        * `play_analysis`
        * `study_recommendation`
    * The Python code decodes this JSON and passes the text strings to the UI for display.

---

## 💾 Data Schema (SQLite)

The database `data/bridge_master.db` typically contains:

* **`hands` Table:**
    * `id`: Unique Deal ID.
    * `pbn`: The portable bridge notation string (standard format).
    * `dealer`: Who dealt (N/S/E/W).
    * `vulnerability`: (None, All, NS, EW).
