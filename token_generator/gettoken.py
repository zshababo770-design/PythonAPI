from flask import Flask, request, jsonify, render_template_string
import hashlib
import requests

# ============================
# Configuration
# ============================
EndPoint = "/"
GPort = 8080

api_key = "4cfe6XXXXXXXXXXXXXXXXX0c3c"  # YOUR_API_KEY
api_secret = "2025.f09ffXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX43777f2e3"  # YOUR_SECRET_KEY

AUTH_URL = "https://auth.flattrade.in/"
TOKEN_URL = "https://authapi.flattrade.in/trade/apitoken"

# Display login URL
print(
    f"{'*- '*50}\n"
    f"Click the link below to authenticate:\n"
    f"{'*- '*50}\n\n"
    f"{AUTH_URL}?app_key={api_key}\n\n"
    f"{'*- '*50}"
)

app = Flask(__name__)


# Generate API hash
def generate_hash(api_key, request_token, api_secret):
    raw_value = f"{api_key}{request_token}{api_secret}"
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


# Request API token
def get_api_token(payload):
    try:
        response = requests.post(
            TOKEN_URL,
            json=payload,
            timeout=15
        )

        # Try to parse JSON even for API-level errors
        try:
            data = response.json()
        except ValueError:
            return {
                "error": "InvalidResponse",
                "details": response.text
            }

        if response.ok:
            return data

        return {
            "error": f"HTTP {response.status_code}",
            "details": data
        }

    except requests.exceptions.Timeout:
        return {
            "error": "Timeout",
            "details": "Flattrade authentication API timed out."
        }

    except requests.exceptions.RequestException as e:
        return {
            "error": "RequestException",
            "details": str(e)
        }


html_template = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Flattrade Client Token</title>

    <script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-gradient-to-br from-blue-50 to-indigo-100
             flex items-center justify-center min-h-screen
             p-4 font-sans">

    <div class="bg-white rounded-xl shadow-lg p-6
                w-full max-w-md space-y-4">

        <div class="flex items-center gap-3">

            <div class="bg-gradient-to-r from-blue-600 to-indigo-600
                        text-white font-bold w-10 h-10 rounded-lg
                        flex items-center justify-center">
                FT
            </div>

            <div>
                <h1 class="text-xl font-bold text-gray-800">
                    Client Data
                </h1>

                <div class="text-xs text-blue-600">
                    Authentication Details
                </div>
            </div>

        </div>

        <div class="space-y-3">

            <div class="flex justify-between items-center
                        bg-gray-50 p-3 rounded-lg">

                <span class="text-sm font-medium">
                    Client ID
                </span>

                <div class="flex items-center gap-2">

                    <span id="client-id"
                          class="text-sm font-mono">
                        {{ api_key }}
                    </span>

                    <button data-copy="client-id"
                            class="text-blue-500 hover:text-blue-700">
                        📋
                    </button>

                </div>
            </div>

            <div class="flex justify-between items-center
                        bg-gray-50 p-3 rounded-lg">

                <span class="text-sm font-medium">
                    Status
                </span>

                <span class="px-2 py-1 bg-green-100
                             text-green-800 text-xs
                             font-bold rounded-full">
                    {{ status }}
                </span>

            </div>

            <div class="bg-gray-50 p-3 rounded-lg">

                <div class="flex justify-between items-center mb-2">

                    <span class="text-sm font-medium">
                        Token
                    </span>

                    <button data-copy="token"
                            class="text-blue-500 hover:text-blue-700">
                        📋
                    </button>

                </div>

                <div id="token"
                     class="font-mono text-xs bg-white p-2
                            rounded border border-gray-200 break-all">
                    {{ token }}
                </div>

            </div>

        </div>

        <div class="text-sm text-center text-gray-500 italic">
            {{ message }}
        </div>

    </div>

    <script>
        document.querySelectorAll("[data-copy]").forEach(btn => {

            btn.onclick = async () => {

                const element =
                    document.getElementById(btn.dataset.copy);

                if (!element) {
                    return;
                }

                try {
                    await navigator.clipboard.writeText(
                        element.textContent.trim()
                    );

                    btn.textContent = "✅";

                    setTimeout(() => {
                        btn.textContent = "📋";
                    }, 1500);

                } catch (error) {
                    console.error("Copy failed:", error);
                }
            };
        });
    </script>

</body>
</html>
"""


# API Endpoint
@app.route(EndPoint, methods=["GET"])
def generate_secret():

    request_token = request.args.get("code", "").strip()

    if not request_token:
        return jsonify({
            "error": "Missing code in query parameters"
        }), 400

    try:
        hashed_secret = generate_hash(
            api_key,
            request_token,
            api_secret
        )

        payload = {
            "api_key": api_key,
            "request_code": request_token,
            "api_secret": hashed_secret
        }

        # Don't print the secret/hash/token to logs.
        print("Authentication request received.")

        response_data = get_api_token(payload)

        if response_data.get("error") is None:

            print(
                "Authentication response status:",
                response_data.get("stat", "Unknown")
            )

            return render_template_string(
                html_template,
                api_key=response_data.get("client", api_key),
                status=response_data.get("stat", "Unknown"),
                message=response_data.get("emsg", ""),
                token=response_data.get("token", "No Token")
            )

        return jsonify(response_data), 502

    except Exception as e:
        # Prevent an unexpected exception from crashing the request.
        app.logger.exception("Authentication failed")

        return jsonify({
            "error": "AuthenticationFailed",
            "details": str(e)
        }), 500


# Simple health-check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok"
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=GPort,
        debug=False
    )
