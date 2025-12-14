import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS so your local script can talk to this server

# Get Token from Koyeb Environment Variables
TOKENS_RAW = os.environ.get("AI_SERVICE_TOKEN", "")
# Handle multiple tokens separated by commas
TOKENS = [t.strip() for t in TOKENS_RAW.split(",") if t.strip()]

@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "platform": "Koyeb",
        "tokens_loaded": len(TOKENS)
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    if not TOKENS:
        return jsonify({"error": "No API Keys found on server"}), 500

    data = request.json
    filename = data.get("filename")
    
    # Try tokens one by one if the first one fails
    for i, token in enumerate(TOKENS):
        try:
            url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                # Important: Look like a browser to avoid blocking
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    { "role": "system", "content": 'Return ONLY raw JSON: {"title": "...", "year": "...", "isSeries": false}' },
                    { "role": "user", "content": f'Analyze: "{filename}"' }
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }

            # Timeout after 10 seconds
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                # Clean up markdown
                clean_content = content.replace("```json", "").replace("```", "").strip()
                return jsonify({"result": clean_content})
            
            elif response.status_code == 429:
                print(f"Token {i} Rate Limited. Trying next...")
                continue # Try next token
            else:
                print(f"Token {i} Error: {response.status_code}")
                continue

        except Exception as e:
            print(f"Connection Error: {e}")
            continue

    return jsonify({"error": "All tokens failed (Rate Limited or Blocked)"}), 500

if __name__ == '__main__':
    # Koyeb expects the app to listen on port 8000 by default
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
