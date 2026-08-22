import json
import random
from pathlib import Path


old_file = Path(
    "/root/autodl-tmp/gemma4_learning_agent/data/lora_data/data/lora_train_300.jsonl"
)

new_file = Path(
    "/root/autodl-tmp/gemma4_learning_agent/app/data/lora_data/lora_train_v2_knowledge_400.jsonl"
)

out_file = Path(
    "/root/autodl-tmp/gemma4_learning_agent/app/data/lora_data/lora_train_v2_577.jsonl"
)


rows=[]


for file in [old_file,new_file]:

    with file.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            if line.strip():

                rows.append(
                    json.loads(line)
                )


# 去重
seen=set()
result=[]


for item in rows:

    q=""

    if "messages" in item:

        for m in item["messages"]:

            if m["role"]=="user":

                q=m["content"]
                break

    else:

        q=item.get(
            "instruction",
            ""
        )


    if q not in seen:

        seen.add(q)
        result.append(item)


random.seed(42)
random.shuffle(result)


with out_file.open(
    "w",
    encoding="utf-8"
) as f:

    for x in result:

        f.write(
            json.dumps(
                x,
                ensure_ascii=False
            )
            + "\n"
        )


print("完成")
print("总数量:",len(result))
print("输出:",out_file)
