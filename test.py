from flask import Flask, request, jsonify
import requests
import os
from pyngrok import ngrok

# Set the Ngrok auth token
os.environ['NGROK_AUTHTOKEN'] = '2fonTlQbIR92QYauNONN23SHGgX_7FnioUn3T35dwAMgDWPQW'

# Authenticate using the token from the environment variable
ngrok.set_auth_token(os.environ['NGROK_AUTHTOKEN'])

# Start an Ngrok tunnel to your local Flask app (running on port 8000)
public_url = ngrok.connect(8000)

# Print the public URL for the tunnel
print(f"Ngrok Tunnel URL: {public_url}")


app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running on port 7860"

@app.route('/test-request', methods=['GET'])
def test_request():
    public_url = request.args.get('url')
    if not public_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        response = requests.get(public_url)
        if response.status_code == 200:
            return "Server is running"
        else:
            return jsonify({"error": "Failed to reach the public URL"}), 500
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)  # Ensure to bind to 0.0.0.0
