import requests
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# === Config from your JSON ===
CLIENT_ID = "126090717874-s0dvttu8qifth23v95tbgucqj5ugdaq0.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:4100/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "openid email profile https://www.googleapis.com/auth/drive"

# === Step 1: Open browser for login ===
auth_url = (
    f"{AUTH_URL}"
    f"?client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    f"&response_type=code"
    f"&scope={SCOPE.replace(' ', '%20')}"
    f"&access_type=offline"
    f"&prompt=consent"
)

print(f"🔗 Opening browser to login...\n{auth_url}")
webbrowser.open(auth_url)

# === Step 2: Create temporary server to catch redirect ===
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<h1>✅ Authorization successful! You may close this window.</h1>".encode('utf-8'))
            print(f"\n📥 Received code: {code}")
            exchange_code_for_token(code)
        else:
            self.send_error(400, "Code not found in request")

def exchange_code_for_token(code):
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    res = requests.post(TOKEN_URL, data=data)
    tokens = res.json()
    print("✅ Token response:")
    print(json.dumps(tokens, indent=4))

    with open("token.json", "w") as f:
        json.dump(tokens, f, indent=4)
        print("💾 Saved token to token.json")

    # Exit server after token is received
    import sys
    sys.exit()

# Run temporary HTTP server to receive the code
print("🌐 Waiting for Google to redirect to http://localhost:4100/code ...")
server = HTTPServer(('localhost', 4100), OAuthHandler)
server.serve_forever()
