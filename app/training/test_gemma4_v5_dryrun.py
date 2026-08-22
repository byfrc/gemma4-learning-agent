from __future__ import annotations

"""
Gemma4-12B-it v5 QLoRA training script.

Gemma4-12B-it 服务器 QLoRA 训练脚本。
来源：根据原项目 training/lora_train_gemma4.py 的数据格式和文本 LoRA 目标规则改造。
用途：A800 80GB 上训练 4bit QLoRA；不用于 Windows 本地。
"""

import torch
import json

from pathlib import Path


from transformers import (
    AutoProcessor,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)


from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)



def load_one_sample(path):

    with Path(path).open(
        encoding="utf-8"
    ) as f:

        for line in f:

            if line.strip():

                item=json.loads(line)

                return item["messages"]


    raise RuntimeError(
        "No data found"
    )





def find_targets(model):

    suffixes=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ]


    exclude=(
        "vision",
        "image",
        "audio",
        "tower",
        "projector"
    )


    names=[]


    for name,module in model.named_modules():

        low=name.lower()


        if not isinstance(
            module,
            torch.nn.Linear
        ):
            continue


        if any(
            x in low
            for x in exclude
        ):
            continue


        if any(
            name.endswith(x)
            for x in suffixes
        ) and (
            "language_model" in low
            or
            ".layers." in low
        ):

            names.append(name)



    names=list(
        dict.fromkeys(names)
    )


    print(
        "LoRA targets:",
        len(names)
    )


    print(
        "\n".join(names[:20])
    )


    return names





def main():


    model_path="/root/autodl-tmp/gemma4_learning_agent/models/gemma/gemma-4-12B-it"


    data_path="/root/autodl-tmp/gemma4_learning_agent/data/lora_data/ai_assistant_lora_1200.jsonl"



    print(
        "Loading processor..."
    )


    processor=AutoProcessor.from_pretrained(
        model_path,
        trust_remote_code=True,
        use_fast=False
    )


    tokenizer=processor.tokenizer


    if tokenizer.pad_token is None:

        tokenizer.pad_token=tokenizer.eos_token



    messages=load_one_sample(
        data_path
    )


    print(
        "\nExample messages:"
    )


    for m in messages:

        print(
            m["role"],
            ":",
            m["content"][:80]
        )



    text=processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )



    inputs=processor(
        text=[text],
        return_tensors="pt",
        truncation=True,
        max_length=2048
    )


    print(
        "Token length:",
        inputs["input_ids"].shape
    )



    print(
        "\nLoading QLoRA model..."
    )


    bnb=BitsAndBytesConfig(

        load_in_4bit=True,

        bnb_4bit_quant_type="nf4",

        bnb_4bit_use_double_quant=True,

        bnb_4bit_compute_dtype=torch.bfloat16

    )



    model=AutoModelForCausalLM.from_pretrained(

        model_path,

        quantization_config=bnb,

        device_map={
            "":0
        },

        torch_dtype=torch.bfloat16,

        trust_remote_code=True,

        attn_implementation="sdpa"

    )



    model.config.use_cache=False



    model=prepare_model_for_kbit_training(
        model
    )



    targets=find_targets(
        model
    )



    config=LoraConfig(

        r=16,

        lora_alpha=32,

        target_modules=targets,

        lora_dropout=0.05,

        bias="none",

        task_type="CAUSAL_LM"

    )



    model=get_peft_model(
        model,
        config
    )


    model.print_trainable_parameters()



    model.train()



    device=next(
        p for p in model.parameters()
        if p.requires_grad
    ).device



    batch={

        k:v.to(device)

        for k,v in inputs.items()

    }



    print(
        "\nForward test..."
    )



    outputs=model(
        **batch,
        labels=batch["input_ids"]
    )


    loss=outputs.loss


    print(
        "Loss:",
        float(loss)
    )



    print(
        "\nBackward test..."
    )


    loss.backward()



    found=False


    for name,param in model.named_parameters():

        if (
            param.requires_grad
            and
            param.grad is not None
        ):

            print(
                "Gradient OK:",
                name
            )

            found=True

            break



    if not found:

        raise RuntimeError(
            "No LoRA gradient detected"
        )



    print(
        "\n===== DRY RUN SUCCESS ====="
    )




if __name__=="__main__":

    main()