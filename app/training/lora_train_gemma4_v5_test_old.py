from __future__ import annotations


"""
Gemma4-12B-it v5 QLoRA training script.

Gemma4-12B-it 服务器 QLoRA 训练脚本。
来源：根据原项目 training/lora_train_gemma4.py 的数据格式和文本 LoRA 目标规则改造。
用途：A100 40GB 上训练 4bit QLoRA；不用于 Windows 本地。

Environment:
    AutoDL A800

Model:
    Gemma4-12B-it

Purpose:
    Fine-tune AI learning assistant / Agent capability.

Training:
    4bit QLoRA + PEFT LoRA
"""


import argparse
import gc
import json
import math
import random

from datetime import datetime
from pathlib import Path


import torch

from torch.utils.data import (
    Dataset,
    DataLoader
)


from transformers import (
    AutoProcessor,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)


from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training
)



class JsonlDataset(Dataset):

    def __init__(
        self,
        rows,
        processor,
        max_length
    ):

        self.rows = rows
        self.processor = processor
        self.max_length = max_length



    def __len__(self):

        return len(self.rows)



    def __getitem__(self, index):

        messages = self.rows[index]["messages"]


        # Gemma4 chat template

        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )


        item = self.processor(
            text=[text],
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=False
        )


        input_ids = item["input_ids"][0]

        attention_mask = item["attention_mask"][0]


        labels = input_ids.clone()



        # =====================================
        # Assistant-only loss
        #
        # system/user:
        #       -100
        #
        # assistant:
        #       calculate loss
        # =====================================


        prompt_messages = []


        for msg in messages:


            if msg["role"] == "assistant":

                break


            prompt_messages.append(msg)



        prompt_text = self.processor.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True
        )


        prompt_tokens = self.processor(
            text=[prompt_text],
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=False
        )


        prompt_len = (
            prompt_tokens["input_ids"]
            .shape[1]
        )


        labels[:prompt_len] = -100



        return {

            "input_ids": input_ids,

            "attention_mask": attention_mask,

            "labels": labels

        }





def collate(
    batch,
    pad_token_id
):


    max_len = max(
        x["input_ids"].shape[0]
        for x in batch
    )


    input_ids = []
    attention_mask = []
    labels = []



    for x in batch:


        pad_len = (
            max_len -
            x["input_ids"].shape[0]
        )


        input_ids.append(
            torch.cat(
                [
                    x["input_ids"],

                    torch.full(
                        (pad_len,),
                        pad_token_id,
                        dtype=torch.long
                    )
                ]
            )
        )


        attention_mask.append(
            torch.cat(
                [
                    x["attention_mask"],

                    torch.zeros(
                        (pad_len,),
                        dtype=torch.long
                    )
                ]
            )
        )


        labels.append(
            torch.cat(
                [
                    x["labels"],

                    torch.full(
                        (pad_len,),
                        -100,
                        dtype=torch.long
                    )
                ]
            )
        )



    return {

        "input_ids":
            torch.stack(input_ids),

        "attention_mask":
            torch.stack(attention_mask),

        "labels":
            torch.stack(labels)

    }





def load_rows(path):


    rows = []



    for line in Path(path).read_text(
        encoding="utf-8"
    ).splitlines():


        if not line.strip():

            continue



        item = json.loads(line)



        # v5 messages format

        if "messages" in item:


            messages = item["messages"]


            roles = {
                x["role"]
                for x in messages
            }



            if (
                "user" in roles
                and
                "assistant" in roles
            ):


                rows.append(
                    {
                        "messages": messages
                    }
                )



        # compatibility

        else:


            q = str(
                item.get("instruction")
                or item.get("question")
                or item.get("prompt")
                or ""
            ).strip()



            a = str(
                item.get("output")
                or item.get("answer")
                or item.get("response")
                or ""
            ).strip()



            if q and a:


                rows.append(
                    {

                        "messages":
                        [

                            {
                                "role":"user",
                                "content":q
                            },

                            {
                                "role":"assistant",
                                "content":a
                            }

                        ]

                    }
                )



    if len(rows) < 2:

        raise RuntimeError(
            "No valid training samples found."
        )



    print(
        f"Loaded samples: {len(rows)}"
    )


    return rows





def find_targets(
    model,
    target
):


    suffixes = [

        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj"

    ]


    if target == "all":

        suffixes += [

            "gate_proj",
            "up_proj",
            "down_proj"

        ]



    exclude = (

        "vision",
        "image",
        "audio",
        "tower",
        "clip",
        "projector",
        "visual",
        "sound",
        "speech"

    )



    names = []



    for name, module in model.named_modules():


        low = name.lower()



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
            name.endswith(s)
            for s in suffixes
        ) and (
            "language_model" in low
            or
            ".layers." in low
        ):

            names.append(name)



    names = list(
        dict.fromkeys(names)
    )



    if not names:


        raise RuntimeError(
            "No Gemma4 language_model LoRA targets found."
        )



    print(
        "LoRA targets:",
        len(names)
    )


    print(
        "\n".join(names[:30])
    )


    return names
def metric(path, row):

    row = {
        "timestamp": datetime.now().isoformat(),
        **row
    }


    with path.open(
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                row,
                ensure_ascii=False
            )
            +
            "\n"
        )





def args():

    p = argparse.ArgumentParser()



    p.add_argument(
        "--model_path",
        required=True
    )


    p.add_argument(
        "--dataset",
        required=True
    )


    p.add_argument(
        "--output_dir",
        required=True
    )


    p.add_argument(
        "--epochs",
        type=float,
        default=3
    )


    p.add_argument(
        "--eval_size",
        type=int,
        default=120
    )


    p.add_argument(
        "--max_length",
        type=int,
        default=2048
    )


    p.add_argument(
        "--lr",
        type=float,
        default=2e-4
    )


    p.add_argument(
        "--batch",
        type=int,
        default=1
    )


    p.add_argument(
        "--grad_accum",
        type=int,
        default=16
    )


    p.add_argument(
        "--r",
        type=int,
        default=16
    )


    p.add_argument(
        "--alpha",
        type=int,
        default=32
    )


    p.add_argument(
        "--target",
        choices=[
            "attention",
            "all"
        ],
        default="all"
    )


    p.add_argument(
        "--resume_adapter",
        default=""
    )


    return p.parse_args()





def main():


    a = args()



    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA GPU not detected."
        )



    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )



    out = Path(
        a.output_dir
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )



    (
        out /
        "train_config.json"
    ).write_text(
        json.dumps(
            vars(a),
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )



    # ============================
    # Processor
    # ============================


    processor = AutoProcessor.from_pretrained(
        a.model_path,
        trust_remote_code=True,
        use_fast=False
    )



    tokenizer = getattr(
        processor,
        "tokenizer",
        None
    )



    if tokenizer is None:

        raise RuntimeError(
            "Tokenizer not found."
        )



    if tokenizer.pad_token is None:

        tokenizer.pad_token = tokenizer.eos_token



    pad_id = tokenizer.pad_token_id



    # ============================
    # Dataset
    # ============================


    rows = load_rows(
        a.dataset
    )


    random.Random(42).shuffle(rows)



    eval_size = min(
        max(1, a.eval_size),
        len(rows)//10
    )



    eval_rows = rows[:eval_size]

    train_rows = rows[eval_size:]



    print(
        f"train={len(train_rows)}, eval={len(eval_rows)}"
    )



    # ============================
    # QLoRA
    # ============================


    bnb = BitsAndBytesConfig(

        load_in_4bit=True,

        bnb_4bit_quant_type="nf4",

        bnb_4bit_use_double_quant=True,

        bnb_4bit_compute_dtype=torch.bfloat16

    )



    model = AutoModelForCausalLM.from_pretrained(

        a.model_path,

        quantization_config=bnb,

        device_map={
            "":0
        },

        torch_dtype=torch.bfloat16,

        trust_remote_code=True,

        attn_implementation="sdpa"

    )



    model.config.use_cache = False



    model = prepare_model_for_kbit_training(

        model,

        use_gradient_checkpointing=True

    )


    model.gradient_checkpointing_enable()



    # ============================
    # LoRA
    # ============================


    targets = find_targets(
        model,
        a.target
    )



    print(
        "LoRA layer number:",
        len(targets)
    )



    config = LoraConfig(

        r=a.r,

        lora_alpha=a.alpha,

        target_modules=targets,

        lora_dropout=0.05,

        bias="none",

        task_type="CAUSAL_LM"

    )



    model = get_peft_model(
        model,
        config
    )



    model.print_trainable_parameters()



    model.train()



    # ============================
    # DataLoader
    # ============================


    train_loader = DataLoader(

        JsonlDataset(
            train_rows,
            processor,
            a.max_length
        ),

        batch_size=a.batch,

        shuffle=True,

        collate_fn=lambda x:
            collate(
                x,
                pad_id
            )

    )



    eval_loader = DataLoader(

        JsonlDataset(
            eval_rows,
            processor,
            a.max_length
        ),

        batch_size=1,

        shuffle=False,

        collate_fn=lambda x:
            collate(
                x,
                pad_id
            )

    )



    device = next(
        p for p in model.parameters()
        if p.requires_grad
    ).device



    optimizer = torch.optim.AdamW(

        [
            p for p in model.parameters()
            if p.requires_grad
        ],

        lr=a.lr

    )



    log = (
        out /
        "metrics_log.jsonl"
    )



    optimizer.zero_grad(
        set_to_none=True
    )



    step = 0

    micro = 0

    total_loss = 0.0



    # ============================
    # Training
    # ============================


    for epoch in range(
        math.ceil(a.epochs)
    ):


        print(
            f"Epoch {epoch+1}/{math.ceil(a.epochs)}"
        )


        for batch in train_loader:


            batch = {

                k:v.to(device)

                for k,v in batch.items()

            }



            loss = model(
                **batch
            ).loss



            if not loss.requires_grad:

                raise RuntimeError(
                    "Loss has no gradient."
                )



            (
                loss /
                a.grad_accum
            ).backward()



            total_loss += float(
                loss.detach().cpu()
            )

            micro += 1



            if micro % a.grad_accum == 0:


                optimizer.step()


                optimizer.zero_grad(
                    set_to_none=True
                )


                step += 1



                train_loss = (
                    total_loss /
                    micro
                )


                metric(
                    log,
                    {
                        "step":step,
                        "epoch":epoch+1,
                        "split":"train",
                        "loss":train_loss
                    }
                )



                print(
                    {
                        "step":step,
                        "loss":train_loss
                    }
                )



                gc.collect()

                torch.cuda.empty_cache()



    # ============================
    # Save
    # ============================


    adapter = (
        out /
        "adapter"
    )


    model.save_pretrained(
        adapter
    )


    try:

        processor.save_pretrained(
            adapter
        )

    except Exception:

        pass



    print(
        "Saved adapter:",
        adapter
    )





if __name__ == "__main__":

    main()