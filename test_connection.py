import os
import asyncio
from dotenv import load_dotenv
import opengradient as og

load_dotenv()

llm = og.LLM(private_key=os.getenv("OG_PRIVATE_KEY"))

# Approve $OPG spending once
llm.ensure_opg_approval(opg_amount=5.0)

async def main():
    result = await llm.chat(
        model=og.TEE_LLM.CLAUDE_SONNET_4_6,
        messages=[
            {"role": "user", "content": "Say hello in one sentence."}
        ],
        max_tokens=50
    )
    print("Response:", result.chat_output['content'])
    print("Payment hash:", result.payment_hash)

asyncio.run(main())
