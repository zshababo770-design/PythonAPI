import hashlib
import os
from urllib.parse import urlencode

import requests
from flask import Flask, request, jsonify, render_template_string

# ============================
# Configuration
# ============================
# Set these in your environment instead of hard-coding them:
#   export FLATTRADE_API_KEY="..."
#   export FLATTRADE_API_SECRET="..."
API_KEY = os.environ.get("FLATTRADE_API_KEY", "")
API_SECRET = os.environ.get("FLATTRADE_API_SECRET", "")

END_POINT = os.environ.get("FLATTRADE_ENDPOINT", "/")
HOST = os.environ.get("FLATTRADE_HOST", "127.0.0.1")  # use 0.0.0.0 only if you need remote access
PORT = int(os.environ.get("FLATTRADE_PORT", "8080"))

AUTH_URL = "https://auth.flattrade.in/"
TOKEN_URL = "https://authapi.flattrade.in/trade/apitoken"
REQUEST_TIMEOUT = 15

if not API_KEY or not API_SECRET:
    raise SystemExit(
        "Missing credentials: set FLATTRADE_API_KEY and FLATTRADE_API_SECRET."
    )

login_url = f"{AUTH_URL}?{urlencode({'app_key': API_KEY})}"
print(
    f"{'*- ' * 50}\n"
    f"Click the link below to authenticate:\n"
    f"{'*- ' * 50}\n\n"
    f"{login_url}\n\n"
    f"{'*- ' * 50}"
)

app = Flask(__name__)


def generate_hash(api_key: str, request_token: str, api_secret: str) -> str:
    raw_value = f"{api_key}{request_token}{api_secret}"
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def get_api_token(payload: dict) -> dict:
    try:
        response = requests.post(TOKEN_URL, json=payload, timeout=REQUEST_TIMEOUT)

        try:
            data = response.json()
        except ValueError:
            return {"error": "InvalidResponse", "details": response.text}

        if response.ok:
            return data

        return {"error": f"HTTP {response.status_code}", "details": data}

    except requests.exceptions.Timeout:
        return {"error": "Timeout", "details": "Flattrade authentication API timed out."}
    except requests.exceptions.RequestException as e:
        return {"error": "RequestException", "details": str(e)}


html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flattrade Client Token</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-gradient-to-br from-blue-50 to-indigo-100
             flex items-center justify-center min-h-screen p-4 font-sans">

    <div class="bg-white rounded-xl shadow-lg p-6 w-full max-w-md space-y-4">

        <div class="flex items-center gap-3">
            <div class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white
                        font-bold w-10 h-10 rounded-lg flex items-center justify-center">
                FT
            </div>
            <div>
                <h1 class="text-xl font-bold text-gray-800">Client Data</h1>
                <div class="text-xs text-blue-600">Authentication Details</div>
            </div>
        </div>

        <div class="space-y-3">

            <div class="flex justify-between items-center bg-gray-50 p-3 rounded-lg">
                <span class="text-sm font-medium">Client ID</span>
                <div class="flex items-center gap-2">
                    <span id="client-id" class="text-sm font-mono">{{ client }}</span>
                    <button data-copy="client-id" class="text-blue-500 hover:text-blue-700">📋</button>
                </div>
            </div>

            <div class="flex justify-between items-center bg-gray-50 p-3 rounded-lg">
                <span class="text-sm font-medium">Status</span>
                <span class="px-2 py-1 text-xs font-bold rounded-full
                             {{ 'bg-green-100 text-green-800' if ok else 'bg-red-100 text-red-800' }}">
                    {{ status }}
                </span>
            </div>

            {% if ok %}
            <div class="bg-gray-50 p-3 rounded-lg">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-sm font-medium">Token</span>
                    <button data-copy="token" class="text-blue-500 hover:text-blue-700">📋</button>
                </div>
                <div id="token"
                     class="font-mono text-xs bg-white p-2 rounded border border-gray-200 break-all">{{ token }}</div>
            </div>
            {% endif %}

        </div>

        {% if message %}
        <div class="text-sm text-center text-gray-500 italic">{{ message }}</div>
        {% endif %}

    </div>

    <script>
        document.querySelectorAll("[data-copy]").forEach(btn => {
            btn.onclick = async () => {
                const el = document.getElementById(btn.dataset.copy);
                if (!el) return;
                try {
                    await navigator.clipboard.writeText(el.textContent.trim());
                    btn.textContent = "✅";
                    setTimeout(() => { btn.textContent = "📋"; }, 1500);
                } catch (error) {
                    console.error("Copy failed:", error);
                }
            };
        });
    </script>
</body>
</html>
"""


@app.after_request
def no_cache(resp):
    # The page contains a live token; keep it out of caches and referrers.
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.route(END_POINT, methods=["GET"])
def generate_secret():
    request_token = request.args.get("code", "").strip()

    if not request_token:
        return jsonify({"error": "Missing code in query parameters"}), 400

    try:
        payload = {
            "api_key": API_KEY,
            "request_code": request_token,
            "api_secret": generate_hash(API_KEY, request_token, API_SECRET),
        }

        print("Authentication request received.")
        data = get_api_token(payload)

        if data.get("error") is not None:
            return jsonify(data), 502

        stat = data.get("stat", "Unknown")
        ok = stat == "Ok"
        print("Authentication response status:", stat)

        return render_template_string(
            html_template,
            client=data.get("client", API_KEY),
            status=stat,
            ok=ok,
            message=data.get("emsg", ""),
            token=data.get("token", ""),
        ), (200 if ok else 401)

    except Exception:
        app.logger.exception("Authentication failed")
        # Don't leak internals to the browser.
        return jsonify({"error": "AuthenticationFailed"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)
