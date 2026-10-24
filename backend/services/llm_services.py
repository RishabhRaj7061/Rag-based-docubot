
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def generate_answer(question: str, context: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is missing. Check your project's .env file."
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are DocuMind AI, a document question-answering "
                    "assistant. Answer using only the supplied context. "
                    "If the answer is missing, say the documents do not "
                    "provide enough information. Do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0.2,
        max_completion_tokens=700,
    )

    answer = response.choices[0].message.content
    return answer or "I could not generate an answer."
