"""Google Calendar OAuth2 authentication module."""

import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

TOKEN_DIR = Path.home() / ".google-calendar-widget"
TOKEN_PATH = TOKEN_DIR / "token.json"
CREDENTIALS_PATH = TOKEN_DIR / "client_secret.json"


def ensure_token_dir() -> None:
    """Create the token directory if it doesn't exist."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)


def get_embedded_client_config() -> Optional[dict]:
    """Retrieve embedded client config dictionary if defined."""
    try:
        from calendar_widget.client_config import EMBEDDED_CLIENT_CONFIG
        if EMBEDDED_CLIENT_CONFIG and isinstance(EMBEDDED_CLIENT_CONFIG, dict):
            return EMBEDDED_CLIENT_CONFIG
    except ImportError:
        pass
    return None


def get_client_secret_path() -> Optional[Path]:
    """Find client_secret.json in project root, working dir, or user dir."""
    project_root = Path(__file__).resolve().parent.parent
    pkg_dir = Path(__file__).resolve().parent

    candidates = [
        # Project root directory
        project_root / "client_secret.json",
        project_root / "credentials.json",
        # Current working directory
        Path.cwd() / "client_secret.json",
        Path.cwd() / "credentials.json",
        # Package directory
        pkg_dir / "client_secret.json",
        # User home config directory
        CREDENTIALS_PATH,
    ]

    # Support PyInstaller bundles / standalone builds
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.insert(0, exe_dir / "client_secret.json")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / "client_secret.json")

    for path in candidates:
        if path.is_file():
            return path

    return None


def has_client_secret() -> bool:
    """Check if valid client credentials exist (file or embedded config)."""
    if get_client_secret_path() is not None:
        return True
    if get_embedded_client_config() is not None:
        return True
    return False


def is_authenticated() -> bool:
    """Check if valid user credentials exist."""
    if not TOKEN_PATH.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(creds)
            return True
    except Exception:
        return False
    return False


def get_credentials() -> Optional[Credentials]:
    """Get valid credentials, refreshing if necessary."""
    if not TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(creds)
            return creds
    except Exception:
        return None
    return None


def save_credentials(creds: Credentials) -> None:
    """Save credentials to token file."""
    ensure_token_dir()
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def authenticate() -> Optional[Credentials]:
    """Run the OAuth2 authentication flow.

    Returns credentials if successful, None otherwise.
    """
    ensure_token_dir()

    secret_path = get_client_secret_path()
    embedded_config = get_embedded_client_config()

    if not secret_path and not embedded_config:
        return None

    try:
        if secret_path:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secret_path), SCOPES
            )
        else:
            flow = InstalledAppFlow.from_client_config(
                embedded_config, SCOPES
            )

        success_msg = (
            "Autenticação concluída com sucesso! "
            "Você já pode fechar esta aba e voltar ao Google Calendar Widget."
        )

        try:
            creds = flow.run_local_server(
                port=8090,
                open_browser=True,
                success_message=success_msg,
            )
        except OSError:
            # Fallback to port 0 (dynamic port) if 8090 is in use
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                success_message=success_msg,
            )

        save_credentials(creds)
        return creds
    except Exception as e:
        print(f"[OAuth Error] Falha na autenticação: {e}")
        return None


def open_setup_instructions() -> None:
    """Open browser with instructions to set up Google Calendar API."""
    url = "https://console.cloud.google.com/apis/credentials"
    webbrowser.open(url)


def save_client_secret(client_secret_data: dict) -> None:
    """Save client secret JSON data to file."""
    ensure_token_dir()
    with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
        json.dump(client_secret_data, f, indent=2)

    # Also save to project root if writable for convenience
    try:
        project_root = Path(__file__).resolve().parent.parent
        project_secret = project_root / "client_secret.json"
        with open(project_secret, "w", encoding="utf-8") as f:
            json.dump(client_secret_data, f, indent=2)
    except Exception:
        pass


def logout() -> None:
    """Remove stored credentials."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
