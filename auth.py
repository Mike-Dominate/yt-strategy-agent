"""One-shot Google OAuth flow. Writes token.pickle in the repo root."""

from __future__ import annotations

import pickle
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

ROOT = Path(__file__).parent
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN_PATH = ROOT / "token.pickle"
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        with TOKEN_PATH.open("rb") as fh:
            creds = pickle.load(fh)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0)
    with TOKEN_PATH.open("wb") as fh:
        pickle.dump(creds, fh)
    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print(f"Signed in. Token saved to {TOKEN_PATH}")
