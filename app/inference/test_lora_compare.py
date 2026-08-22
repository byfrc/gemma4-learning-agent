import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel


BASE_MODEL = "/root/autodl-tmp/gemma4_learning_agent/models/gemma/gemma-4-12B-it"

ADAPTER = "/root/autodl-tmp/gemma4_learning_agent/models/lora/gemma4_learning_v1/adapter"


QUESTIONS = [
    "我完全不会人工智能，应该怎么开始学习？",
    "RAG是不是重新训练模型？",
    "帮我制定一个两周人工智能学习计划。",
]


def load_base():

    print("加载 Base Gemma4...")

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



def generate(model, tokenizer, prompt):

    messages=[
        {
            "role":"user",
            "content":prompt
        }
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )


    inputs = tokenizer(
        text,
        return_tensors="pt"
    ).to(model.device)


    with torch.no_grad():

        outputs=model.generate(
            **inputs,
            max_new_tokens=300,
            temperature=0.7,
            do_sample=True,
        )


    result = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )

    return result



def main():

    base_model, tokenizer = load_base()


    print("\n========== Base Gemma4 ==========")

    base_results=[]

    for q in QUESTIONS:

        ans=generate(
            base_model,
            tokenizer,
            q
        )

        base_results.append(ans)

        print("\n问题:")
        print(q)

        print("\n回答:")
        print(ans)



    print("\n加载 LoRA Adapter...")

    lora_model=PeftModel.from_pretrained(
        base_model,
        ADAPTER
    )

    print("\n========== LoRA Gemma4 ==========")


    for q in QUESTIONS:

        ans=generate(
            lora_model,
            tokenizer,
            q
        )

        print("\n问题:")
        print(q)

        print("\n回答:")
        print(ans)



if __name__=="__main__":
    main()
