import torch

from transformers import (
    AutoProcessor,
    AutoModelForCausalLM
)

from peft import PeftModel


BASE_MODEL = "/root/autodl-tmp/gemma4_learning_agent/models/gemma/gemma-4-12B-it"

ADAPTER = "/root/autodl-tmp/gemma4_learning_agent/models/lora/gemma4_learning_v5/adapter"


print("Loading processor...")


processor = AutoProcessor.from_pretrained(
    ADAPTER,
    trust_remote_code=True
)


print("Loading base model...")


model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)


print("Loading adapter...")


model = PeftModel.from_pretrained(
    model,
    ADAPTER
)


model.eval()


def generate(question):

    messages = [
        {
            "role": "system",
            "content":
            "你是一名AI学习助手。帮助用户理解人工智能知识，回答要求准确、清晰、适合初学者。"
        },
        {
            "role": "user",
            "content": question
        }
    ]


    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )


    inputs = processor(
        text=[text],
        return_tensors="pt"
    )


    inputs = {
        k:v.to(model.device)
        for k,v in inputs.items()
    }


    with torch.no_grad():

        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.6,
            top_p=0.9,
            do_sample=True
        )
    response = processor.batch_decode(
    outputs,
    skip_special_tokens=True
    )[0]

    if "model\nthought" in response:
        response = response.split("model\nthought")[-1]

    if "thought" in response:
        response = response.replace(
            "thought",
             ""
        )


    print("\n====================")
    print(response)
    print("====================")


if __name__=="__main__":

    while True:

        q=input("\nUser: ")

        if q=="exit":
            break

        generate(q)