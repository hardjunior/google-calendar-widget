"""Optional embedded Google OAuth client configuration.

If a client_secret.json file is found in the project root or user directory,
it will take precedence. You can also embed the OAuth client JSON dict here
to distribute the application without requiring a separate credentials file.
"""

from typing import Optional

# Set this to your OAuth client JSON dict (from Google Cloud Console) if desired:
# EMBEDDED_CLIENT_CONFIG = {
#     "installed": {
#         "client_id": "...",
#         "project_id": "...",
#         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#         "token_uri": "https://oauth2.googleapis.com/token",
#         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#         "client_secret": "...",
#         "redirect_uris": ["http://localhost"]
#     }
# }
EMBEDDED_CLIENT_CONFIG: Optional[dict] = None
