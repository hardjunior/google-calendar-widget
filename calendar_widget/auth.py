"""Google Calendar OAuth2 authentication module."""

import json
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


def has_client_secret() -> bool:
    """Check if the client_secret.json file exists."""
    return CREDENTIALS_PATH.exists()


def is_authenticated() -> bool:
    """Check if valid credentials exist."""
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
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def authenticate() -> Optional[Credentials]:
    """Run the OAuth2 authentication flow.

    Returns credentials if successful, None otherwise.
    """
    ensure_token_dir()

    if not has_client_secret():
        return None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH), SCOPES
        )
        creds = flow.run_local_server(
            port=8090,
            open_browser=True,
            success_message=(
                "Autenticação concluída! Pode fechar esta janela e "
                "voltar ao widget."
            ),
        )
        save_credentials(creds)
        return creds
    except Exception:
        return None


def open_setup_instructions() -> None:
    """Open browser with instructions to set up Google Calendar API."""
    url = "https://console.cloud.google.com/apis/credentials"
    webbrowser.open(url)


def save_client_secret(client_secret_data: dict) -> None:
    """Save client secret JSON data to file."""
    ensure_token_dir()
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(client_secret_data, f)


def logout() -> None:
    """Remove stored credentials."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
