import json
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)
from peft import PeftModel


BASE_MODEL = (
    "/root/autodl-tmp/gemma4_learning_agent/"
    "models/gemma/gemma-4-12B-it"
)

ADAPTER = (
    "/root/autodl-tmp/gemma4_learning_agent/"
    "models/lora/gemma4_learning_v1/adapter"
)


OUTPUT = Path(
    "/root/autodl-tmp/gemma4_learning_agent/results"
)

OUTPUT.mkdir(exist_ok=True)


QUESTIONS = [
    "我完全不会人工智能，应该怎么开始学习？",

    "RAG是不是重新训练模型？",

    "帮我制定一个两周人工智能学习计划。"
]


def load_model():

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )


    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb,
        device_map={"":0},
        trust_remote_code=True,
    )


    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )


    return model, tokenizer



def generate(model, tokenizer, question):

    messages=[
        {
            "role":"user",
            "content":question
        }
    ]


    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )


    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    ).to(model.device)


    with torch.no_grad():

        output=model.generate(
            **inputs,
            max_new_tokens=220,
            temperature=0.7,
            do_sample=True,
        )


    answer = tokenizer.decode(
        output[0][inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )


    return answer



def main():

    model, tokenizer = load_model()


    print("生成 Base 结果...")


    base_results=[]

    for q in QUESTIONS:

        ans=generate(
            model,
            tokenizer,
            q
        )

        base_results.append(
            {
                "question":q,
                "answer":ans
            }
        )


    print("加载 LoRA...")


    lora_model=PeftModel.from_pretrained(
        model,
        ADAPTER
    )


    print("生成 LoRA 结果...")


    lora_results=[]


    for q in QUESTIONS:

        ans=generate(
            lora_model,
            tokenizer,
            q
        )


        lora_results.append(
            {
                "question":q,
                "answer":ans
            }
        )


    result={
        "base":base_results,
        "lora":lora_results
    }


    with open(
        OUTPUT/"lora_compare_results.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )


    with open(
        OUTPUT/"lora_compare_results.md",
        "w",
        encoding="utf-8"
    ) as f:


        f.write("# Gemma4 LoRA 微调效果对比\n\n")


        for i,q in enumerate(QUESTIONS):

            f.write(
                f"## Case {i+1}\n\n"
            )

            f.write(
                f"### 问题\n{q}\n\n"
            )


            f.write(
                "### Base Gemma4\n\n"
            )

            f.write(
                base_results[i]["answer"]
                +
                "\n\n"
            )


            f.write(
                "### LoRA Gemma4\n\n"
            )

            f.write(
                lora_results[i]["answer"]
                +
                "\n\n"
            )


    print("完成")
    print(OUTPUT)



if __name__=="__main__":
    main()
