import json
from pathlib import Path

from transformers import AutoProcessor


model_path="/root/autodl-tmp/gemma4_learning_agent/models/gemma/gemma-4-12B-it"

data_path="/root/autodl-tmp/gemma4_learning_agent/data/lora_data/ai_assistant_lora_1200.jsonl"


processor=AutoProcessor.from_pretrained(
    model_path,
    trust_remote_code=True,
    use_fast=False
)


row=json.loads(
    Path(data_path)
    .read_text(encoding="utf-8")
    .splitlines()[0]
)


messages=row["messages"]


text=processor.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=False
)


full=processor(
    text=[text],
    return_tensors="pt"
)


ids=full["input_ids"][0]


prompt_messages=[]

for msg in messages:

    if msg["role"]=="assistant":
        break

    prompt_messages.append(msg)



prompt_text=processor.apply_chat_template(
    prompt_messages,
    tokenize=False,
    add_generation_prompt=True
)


prompt_tokens=processor(
    text=[prompt_text],
    return_tensors="pt"
)


prompt_len=prompt_tokens["input_ids"].shape[1]


labels=ids.clone()

labels[:prompt_len]=-100


print("total tokens:",len(labels))

print(
    "masked tokens:",
    (labels==-100).sum().item()
)

print(
    "assistant tokens:",
    (labels!=-100).sum().item()
)
