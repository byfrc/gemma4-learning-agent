# Gemma4 Learning Agent: Running on Windows

A private learning assistant for AI and Java courses. It runs entirely on your own
PC. Gemma4 answers through Ollama, a FastAPI backend searches the course material
(RAG), and a web page provides chat with image input, a knowledge base and a
Java online IDE.

The Chinese deployment guide with every option is in
[WINDOWS_LOCAL_DEPLOYMENT_GUIDE_CN.md](WINDOWS_LOCAL_DEPLOYMENT_GUIDE_CN.md).

## Requirements

- Windows 10 or 11 (no WSL needed)
- An internet connection for the first start
- About 15 GB of free disk space (the model alone is about 10 GB)
- 16 GB of RAM or more is recommended, because the model runs locally
- `winget` (Windows App Installer) so the launcher can install Java for you.
  Without it, install JDK 17 manually first. Python 3.12 is installed with
  winget too, or downloaded from python.org when winget is missing or fails.

## 1. Get the code

The Windows version lives on the `windows-deploy` branch.

```powershell
git clone -b windows-deploy https://github.com/byfrc/gemma4-learning-agent.git
cd gemma4-learning-agent
```

## 2. (Optional) Change the admin password

The first start creates an admin account `admin` / `admin123`. To use your own
password, copy `app\backend\.env.example` to `app\backend\.env` **before the
first start** and change `AUTH_PASSWORD` and `AUTH_SECRET_KEY`. After the first
start the password is stored in the database, and editing `.env` no longer
changes it.

## 3. Start the program

Double-click `start_windows.bat` in the project folder, or run:

```powershell
.\start_windows.bat
```

The first start takes a while. The launcher shows progress and does the
following:

1. Installs Python 3.12 and Microsoft OpenJDK 17 if they are missing
2. Creates the Python environment `app\.venv-windows` and installs dependencies
3. Installs and starts Ollama
4. Downloads the `gemma4:e4b` model (about 10 GB)
5. Sets up image support: it downloads a vision projector (about 534 MB),
   creates the local model `gemma4-project-vision:e4b` and checks that the model
   can read a test image. This happens only once.
6. Starts the backend and the web page, then opens your browser at
   **http://127.0.0.1:18780**

Log in with the admin account, or register a new account (new accounts are
students). Pick the AI or Java subject on the login page.

Keep the launcher window open while you use the program.

## 4. Stop and start again

- Stop: press `Ctrl+C` in the launcher window, or run `stop_windows.bat`
- Start again: `start_windows.bat`. It skips anything that is already installed.
- Faster start once everything is installed: `start_installed.bat`, which also
  skips the Python dependency check.

## Using images in chat

Attach PNG, JPEG or WebP images to a chat message and ask about them. Up to four
images are used per message. Image support is set up automatically for the
default Ollama model. If setup fails (for example because the network dropped),
the launcher prints a yellow warning, and text chat keeps working. Run
`start_windows.bat` again to retry. Partial downloads resume.

## Launcher options

Add options after the launcher name, for example `.\start_windows.bat -Mode mock`.

| Option | What it does |
|---|---|
| `-Mode mock` | Runs without a model, to check the web page, login, RAG and Java IDE |
| `-Mode lmstudio` | Uses LM Studio instead of Ollama (same as `start_lmstudio_windows.bat`). Automatic image setup only applies to Ollama mode. |
| `-OllamaModel "tag"` | Uses a different Ollama model. Automatic image setup only applies to the default `gemma4:e4b`. |
| `-FrontendPort 18780` / `-ApiPort 8000` | Changes the web page or backend port |
| `-NoBrowser` | Does not open the browser |
| `-InstallOffice` | Installs LibreOffice so legacy `.ppt` files can be uploaded |
| `-SkipInstall` | Skips installing dependencies (what `start_installed.bat` uses) |

## Where things are stored

These folders are created on your PC and are not part of the Git repository:

- `app\backend\data\`: accounts, conversations, uploaded files and chat images
- `app\backend\logs\local_deploy\`: launcher, backend and Ollama logs
- Ollama stores its models in its own folder, outside the project

## Troubleshooting

| Problem | Fix |
|---|---|
| "winget not found" | Install Python 3.12 and JDK 17 manually, reopen PowerShell and start again |
| Python or Java still not found after install | Close the window and start again so the new `PATH` is loaded |
| Model download fails | Check the network and run `ollama pull gemma4:e4b`, then start again |
| Port already in use | Stop the other program, or start with `-FrontendPort` / `-ApiPort` |
| Anything else | Read the logs in `app\backend\logs\local_deploy\` |
