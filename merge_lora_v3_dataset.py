import json
import random
from pathlib import Path


# 修改成你的实际路径
v2_path = Path(
    "/root/autodl-tmp/gemma4_learning_agent/data/lora_data/lora_train_v2.jsonl"
)

v3_path = Path(
    "/root/autodl-tmp/gemma4_learning_agent/data/lora_data/lora_train_v3_expand.jsonl"
)


out_path = Path(
    "/root/autodl-tmp/gemma4_learning_agent/data/lora_data/lora_train_final_v3_1700.jsonl"
)


def convert_old(row):

    if "messages" in row:
        return row

    instruction = (
        row.get("instruction")
        or row.get("question")
        or row.get("prompt")
        or ""
    )

    output = (
        row.get("output")
        or row.get("answer")
        or row.get("response")
        or ""
    )

    if not instruction or not output:
        return None


    return {
        "messages":[
            {
                "role":"system",
                "content":
                "你是一名耐心、专业的AI学习助手，需要帮助学生理解人工智能知识，并提供清晰的学习建议。"
            },
            {
                "role":"user",
                "content":instruction
            },
            {
                "role":"assistant",
                "content":output
            }
        ],
        "metadata":{
            "source":"legacy_lora",
            "type":row.get("agent_type","unknown")
        }
    }


data=[]


# 加载v2
if v2_path.exists():

    with open(v2_path,encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row=json.loads(line)

                item=convert_old(row)

                if item:
                    data.append(item)


# 加载v3
with open(v3_path,encoding="utf-8") as f:

    for line in f:

        if line.strip():

            row=json.loads(line)

            data.append(row)



random.seed(42)
random.shuffle(data)


with open(out_path,"w",encoding="utf-8") as f:

    for item in data:
        f.write(
            json.dumps(
                item,
                ensure_ascii=False
            )
            + "\n"
        )


print("完成")
print("总数量:",len(data))
print("输出:",out_path)
