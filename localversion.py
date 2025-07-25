from transformers import pipeline
import torch

pipe = pipeline(
    "text-generation",
    model="google/gemma-3n-e2b-it",
    device="cpu",
    torch_dtype=torch.bfloat16,
)

while True:
    print("bot ready\n")
    text = input()
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "あなたはサポートアンドロイドです。会話の文体で話してください。"}]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text}
            ]
        }
    ]

    output = pipe(text_inputs=messages, max_new_tokens=200)
    print(output[0]["generated_text"][-1]["content"])