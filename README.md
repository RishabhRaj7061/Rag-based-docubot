# RAG-Based DocuBot 🤖

A document-based chatbot powered by **Retrieval-Augmented Generation (RAG)** that helps users retrieve relevant information from documents through a simple web interface.

## 📌 Project Overview

RAG-Based DocuBot is designed to make document search more convenient by combining document retrieval with a chatbot interface. Instead of manually searching through lengthy documents, users can interact with the application and ask questions about available content.

The project separates the user interface from the backend API, making the application easier to organize and maintain.

## ✨ Features

- Document-oriented question answering
- Retrieval-Augmented Generation (RAG) workflow
- Streamlit-based user interface
- FastAPI backend
- API endpoints accessible through interactive API documentation
- Python virtual environment support

*Note: The exact document formats, language model, vector database, and retrieval capabilities depend on the project's implementation.*

## 🛠️ Technology Stack

- **Python** — Core programming language
- **Streamlit** — Frontend interface
- **FastAPI** — Backend API
- **Uvicorn** — ASGI server
- **RAG** — Retrieval-Augmented Generation architecture

## 📂 Project Structure

```text
rag-based-docubot/
├── backend/
│   └── main.py
├── frontend/
│   └── app.py
├── requirements.txt
├── main.py
├── index_existing.py
└── test_search.py
```

Additional modules and files may be present in the repository.

## ⚙️ Prerequisites

- Python 3.10 or a compatible version for the project's dependencies
- pip
- Git

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/RishabhRaj7061/rag-based-docubot.git
cd rag-based-docubot
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the environment

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## ▶️ Run the Application

Open two terminal windows in the project directory.

### Terminal 1: Start the backend

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Backend health check:

http://127.0.0.1:8000/health

Interactive API documentation:

http://127.0.0.1:8000/docs

### Terminal 2: Start the frontend

```bash
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8502
```

Open the application in your browser:

http://127.0.0.1:8502

## 🧪 Testing

Run the project's search test script, if its required data and configuration are available:

```bash
python test_search.py
```

## 🔒 Data and Configuration

- Keep API keys and credentials out of source control.
- Do not commit private documents, local vector indexes, or other sensitive data.
- Review `.gitignore` before pushing changes.
- Follow the configuration requirements of the project's retrieval and language-model components.

## 🗺️ Future Improvements

Potential enhancements include:

- Support for additional document formats
- Improved retrieval quality
- Source references in answers
- Evaluation of answer accuracy
- Deployment to a cloud platform

## 👨‍💻 Author

**Rishabh Raj**

GitHub: [@RishabhRaj7061](https://github.com/RishabhRaj7061)

## 📄 License

No license has been specified yet. All rights are reserved by default unless a license is added to the repository.
