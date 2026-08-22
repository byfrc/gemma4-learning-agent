import json
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)
from peft import PeftModel


BASE_MODEL = (
    "/root/autodl-tmp/gemma4_learning_agent/"
    "models/gemma/gemma-4-12B-it"
)

V1_ADAPTER = (
    "/root/autodl-tmp/gemma4_learning_agent/"
    "models/lora/gemma4_learning_v1/adapter"
)

V2_ADAPTER = (
    "/root/autodl-tmp/gemma4_learning_agent/"
    "models/lora/gemma4_learning_v2/adapter"
)


OUT = Path(
    "/root/autodl-tmp/gemma4_learning_agent/results"
)

OUT.mkdir(exist_ok=True)


QUESTIONS = [
    "我完全不会人工智能，应该怎么开始学习？",

    "RAG是不是重新训练模型？",

    "帮我制定一个两周人工智能学习计划。"
]


def load_base():

    print("加载 Base Gemma4...")


    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )


    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb,
        device_map={"":0},
        trust_remote_code=True
    )


    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True
    )


    return model, tokenizer



def generate(model, tokenizer, q):

    messages=[
        {
            "role":"user",
            "content":q
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

        outputs=model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.7,
            do_sample=True
        )


    ans=tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )


    return ans



def test_model(model_name, model, tokenizer):

    print("\n测试:", model_name)


    results=[]

    for q in QUESTIONS:

        ans=generate(
            model,
            tokenizer,
            q
        )


        results.append(
            {
                "question":q,
                "answer":ans
            }
        )


        print("\n问题:")
        print(q)

        print("\n回答:")
        print(ans[:300])


    with open(
        OUT/f"{model_name}.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )


    return results



def main():

    base, tokenizer = load_base()


    base_result=test_model(
        "base_answers",
        base,
        tokenizer
    )


    print("\n加载 LoRA v1")

    v1=PeftModel.from_pretrained(
        base,
        V1_ADAPTER
    )


    v1_result=test_model(
        "lora_v1_answers",
        v1,
        tokenizer
    )


    print("\n加载 LoRA v2")


    v2=PeftModel.from_pretrained(
        base,
        V2_ADAPTER
    )


    v2_result=test_model(
        "lora_v2_answers",
        v2,
        tokenizer
    )


    with open(
        OUT/"lora_three_version_compare.md",
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
            "# Gemma4 LoRA 三版本效果对比\n\n"
        )


        for i,q in enumerate(QUESTIONS):

            f.write(
                f"## Case {i+1}\n\n"
            )

            f.write(
                f"### 问题\n{q}\n\n"
            )


            for name,data in [
                ("Base Gemma4",base_result),
                ("LoRA v1",v1_result),
                ("LoRA v2",v2_result)
            ]:

                f.write(
                    f"### {name}\n\n"
                )

                f.write(
                    data[i]["answer"]
                    +
                    "\n\n"
                )


    print("\n完成")
    print(
        "结果目录:",
        OUT
    )


if __name__=="__main__":
    main()
