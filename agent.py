import asyncio
import opengradient as og
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

PRIVATE_KEY = os.getenv("OG_PRIVATE_KEY")
llm = og.LLM(private_key=PRIVATE_KEY)
llm.ensure_opg_approval(opg_amount=5.0)

app = Flask(__name__)
CORS(app)

conversation_history = []

SYSTEM_PROMPT = """You are OGent, a helpful AI agent running on the OpenGradient
decentralized network. Every response is verifiable on-chain via Base Sepolia.
Be concise and helpful. Keep responses under 200 words unless asked for detail."""

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    conversation_history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    try:
        result = asyncio.run(llm.chat(
            model=og.TEE_LLM.CLAUDE_HAIKU_4_5,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        ))

        response_text = result.chat_output.get("content", "")
        tx_hash = result.payment_hash or ""

        conversation_history.append({"role": "assistant", "content": response_text})

        return jsonify({
            "response": response_text,
            "tx_hash": tx_hash,
            "explorer_url": f"https://explorer.opengradient.ai/tx/{tx_hash}",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reset", methods=["POST"])
def reset():
    conversation_history.clear()
    return jsonify({"status": "Conversation reset."})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": "OGent"})

if __name__ == "__main__":
    print("OGent running at http://localhost:5000")
    app.run(debug=True, port=5000)
