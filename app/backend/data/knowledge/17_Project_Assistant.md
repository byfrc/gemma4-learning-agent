# Project Assistant: reference for the Gemma4 learning platform

This document describes the Gemma4 learning platform itself. It does not describe other projects a user may upload.

## Agent definition

Project Assistant uses the mode `project_assistant`. The accepted mode names are defined by `AgentMode` in `app/backend/app/schemas.py`. Its instructions are in `AGENT_PROMPTS` in `app/backend/app/providers.py`. `build_messages` selects those instructions and adds the requested language, retrieved evidence, and conversation history.

## Request flow

The Project Assistant tab is in `app/frontend/index.html`. `app/frontend/app.js` sends the selected `agent_mode` to `POST /api/chat`. `app/backend/app/main.py` authenticates the user, loads the conversation, retrieves relevant documents, and calls the configured model. The Windows Ollama launcher defaults to `gemma4:e4b`.

## Knowledge and history

AI documents are stored in `app/backend/data/knowledge/`. Java documents are stored in `app/backend/data/subjects/java/knowledge/`. Uploading a supported document rebuilds that subject's retrieval index. Conversations, mode names, messages, sources, and feedback use the existing SQLite storage. A user's selected subject controls which knowledge base and conversations they can access.

## Using the agent

Click Files beside the message box, or drop files into the chat. Administrators can upload documents and source files, up to 30 MB each. Upload status shows when a file has been added to the selected track's Knowledge Base. Source formats include PY, JS, TS, JAVA, and JSON; their indentation is preserved for retrieval. The agent reads source files as text and does not execute them. Users can also paste code or errors into chat.

## Local startup

Run `start_installed.bat` for this Windows installation. The launcher defaults to the frontend at `http://127.0.0.1:18780` and the API at `http://127.0.0.1:8000/api`. Ports can be changed with launcher parameters. The API health endpoint is `/api/healthz`. Logs are in `app/backend/logs/local_deploy/`.
