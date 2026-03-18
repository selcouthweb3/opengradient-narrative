import opengradient as og

og.init(
    private_key="0x03c6c30cd9cd0d1cae394d8e264ffc78bf7bf171d5366e5330de155705a5af9c",
    email="jessjay0520@gmail.com",
    password="Artnova05@"
)

tx_hash, finish_reason, response = og.llm_chat(
    model_cid=og.LLM.LLAMA_3_1_8B_INSTRUCT,
    messages=[
        {"role": "user", "content": "Say hello in one sentence."}
    ],
    inference_mode=og.LlmInferenceMode.VANILLA,
    max_tokens=50
)

print("TX Hash:", tx_hash)
print("Response:", response)
