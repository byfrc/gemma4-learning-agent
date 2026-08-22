from __future__ import annotations

# ============================================================
# Gemma4 text-only LoRA training script
# 适用于：google/gemma-4-E2B-it 本地小规模跑通 / AutoDL 后续实操
# 说明：
# - Gemma4 使用 AutoProcessor + AutoModelForImageTextToText
# - 本脚本不依赖 TRL，避免 SFTTrainer / processor 版本适配问题
# - Windows 本地默认 fp16 LoRA，不启用 bitsandbytes 4bit/8bit
# ============================================================

import argparse
import gc
import json
import math
import os
import pathlib
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Windows 下避免某些依赖默认 GBK 读取 jinja/template 文件
_original_read_text = pathlib.Path.read_text
def _read_text_utf8(self, encoding=None, errors=None):
    if encoding is None:
        encoding = "utf-8"
    if errors is None:
        errors = "ignore"
    return _original_read_text(self, encoding=encoding, errors=errors)
pathlib.Path.read_text = _read_text_utf8

import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import AutoProcessor, AutoModelForImageTextToText


class JsonlSFTDataset(Dataset):
    def __init__(self, rows: List[Dict[str, Any]], processor, max_length: int):
        self.rows = rows
        self.processor = processor
        self.max_length = max_length

    def __len__(self):
        return len(self.rows)

    def _safe_join(self, x):
        if isinstance(x, list):
            return "\n".join(map(str, x))
        return str(x or "")

    def _build_text(self, example: Dict[str, Any]) -> str:
        instruction = str(
            example.get("instruction")
            or example.get("question")
            or example.get("prompt")
            or ""
        ).strip()

        context = str(example.get("context") or example.get("input") or "").strip()
        agent_type = str(example.get("agent_type") or "").strip()

        if context:
            instruction = instruction + "\n\n参考上下文：\n" + context
        if agent_type:
            instruction = f"任务类型：{agent_type}\n\n{instruction}"

        if "output" in example or "answer" in example or "response" in example:
            assistant_content = str(
                example.get("output")
                or example.get("answer")
                or example.get("response")
                or ""
            ).strip()
        else:
            assistant_content = (
                f"<think>\n{self._safe_join(example.get('think'))}\n</think>\n"
                f"问题分解:\n{self._safe_join(example.get('decomposition'))}\n\n"
                f"模式识别:\n{self._safe_join(example.get('pattern'))}\n\n"
                f"抽象化:\n{self._safe_join(example.get('abstract'))}\n\n"
                f"算法:\n{self._safe_join(example.get('algorithm'))}\n\n"
                f"参考代码:\n{self._safe_join(example.get('code'))}"
            ).strip()

        if not instruction or not assistant_content:
            return ""

        # Gemma4 是 image-text-to-text，多模态消息格式中 content 是 list
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction}
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": assistant_content}
                ],
            },
        ]

        try:
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
        except Exception:
            # 兜底格式，避免 processor/chat_template 版本问题导致数据为空
            text = (
                f"<start_of_turn>user\n{instruction}<end_of_turn>\n"
                f"<start_of_turn>model\n{assistant_content}<end_of_turn>"
            )
        return text

    def __getitem__(self, idx):
        text = self._build_text(self.rows[idx])
        if not text:
            # 理论上初始化前已过滤；这里兜底
            text = "用户：请简单介绍机器学习。\n助手：机器学习是让模型从数据中学习规律的方法。"

        encoded = self.processor(
            text=[text],
            return_tensors="pt",
            padding=False,
            truncation=True,
            max_length=self.max_length,
        )

        input_ids = encoded["input_ids"][0]
        attention_mask = encoded["attention_mask"][0]
        labels = input_ids.clone()

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def collate_fn(batch, pad_token_id: int):
    max_len = max(x["input_ids"].shape[0] for x in batch)

    input_ids_list, attention_mask_list, labels_list = [], [], []

    for item in batch:
        input_ids = item["input_ids"]
        attention_mask = item["attention_mask"]
        labels = item["labels"]

        pad_len = max_len - input_ids.shape[0]

        if pad_len > 0:
            input_ids = torch.cat([
                input_ids,
                torch.full((pad_len,), pad_token_id, dtype=input_ids.dtype)
            ])
            attention_mask = torch.cat([
                attention_mask,
                torch.zeros((pad_len,), dtype=attention_mask.dtype)
            ])
            labels = torch.cat([
                labels,
                torch.full((pad_len,), -100, dtype=labels.dtype)
            ])

        # padding token 不参与 loss
        labels = labels.masked_fill(input_ids == pad_token_id, -100)

        input_ids_list.append(input_ids)
        attention_mask_list.append(attention_mask)
        labels_list.append(labels)

    return {
        "input_ids": torch.stack(input_ids_list),
        "attention_mask": torch.stack(attention_mask_list),
        "labels": torch.stack(labels_list),
    }


def load_jsonl_rows(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    # 过滤没有指令或没有输出的空样本
    cleaned = []
    for r in rows:
        instruction = str(r.get("instruction") or r.get("question") or r.get("prompt") or "").strip()
        output = str(r.get("output") or r.get("answer") or r.get("response") or "").strip()
        # 兼容算法字段数据
        has_algorithm_style = any(k in r for k in ["think", "decomposition", "pattern", "algorithm", "code"])
        if instruction and (output or has_algorithm_style):
            cleaned.append(r)
    return cleaned


def split_rows(rows: List[Dict[str, Any]], eval_size: int, seed: int = 42):
    random.Random(seed).shuffle(rows)
    if len(rows) < 2:
        raise ValueError("训练数据至少需要2条。")
    eval_size = min(eval_size, max(1, len(rows) // 10))
    eval_rows = rows[:eval_size]
    train_rows = rows[eval_size:]
    if not train_rows:
        train_rows = rows[:-1]
        eval_rows = rows[-1:]
    return train_rows, eval_rows


def find_gemma4_lora_targets(model, target: str):
    """
    自动寻找 Gemma4 纯文本分支可注入 LoRA 的 Linear 层。

    兼容两种情况：
    1. 文本分支是直接 Linear：...q_proj / ...k_proj / ...v_proj / ...o_proj
    2. 某些分支是 wrapper：...q_proj.linear / ...k_proj.linear ...

    重要：
    - 必须排除 audio_tower / vision_tower 等非文本分支；
    - 上一版只找 q_proj.linear，导致如果文本分支是直接 q_proj 就找不到；
    - 这一版同时匹配 q_proj 和 q_proj.linear。
    """
    import torch

    attention_suffixes = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "q_proj.linear", "k_proj.linear", "v_proj.linear", "o_proj.linear",
    ]

    mlp_suffixes = [
        "gate_proj", "up_proj", "down_proj",
        "gate_proj.linear", "up_proj.linear", "down_proj.linear",
    ]

    suffixes = attention_suffixes + mlp_suffixes if target == "all" else attention_suffixes

    excluded_keywords = [
        "vision",
        "visual",
        "image",
        "clip",
        "projector",
        "multi_modal",
        "mm_",
        "audio",
        "sound",
        "speech",
        "tower",
    ]

    preferred_keywords = [
        "language_model",
        "text_model",
        "text_decoder",
        "decoder",
        "llm",
        "model.layers",
        "layers",
    ]

    candidates = []
    preferred = []
    all_linear_names = []

    for name, module in model.named_modules():
        if not isinstance(module, torch.nn.Linear):
            continue

        all_linear_names.append(name)
        lower = name.lower()

        if any(k in lower for k in excluded_keywords):
            continue

        if not any(name.endswith(suf) for suf in suffixes):
            continue

        candidates.append(name)

        if any(k in lower for k in preferred_keywords):
            preferred.append(name)

    matched = preferred if preferred else candidates
    matched = list(dict.fromkeys(matched))

    debug_path = "gemma4_linear_modules_debug.txt"
    try:
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write("==== ALL torch.nn.Linear module names ====\n")
            for n in all_linear_names:
                f.write(n + "\n")
            f.write("\n==== FILTERED LoRA candidates ====\n")
            for n in candidates:
                f.write(n + "\n")
            f.write("\n==== FINAL matched targets ====\n")
            for n in matched:
                f.write(n + "\n")
        print(f"[DEBUG] Linear模块名已保存到：{debug_path}")
    except Exception as e:
        print(f"[WARN] 保存 debug 模块名失败：{e}")

    if not matched:
        print("[WARN] 没有匹配到文本分支可注入 LoRA 的 Linear 层。")
        print("[DEBUG] 前300个 Linear 模块名如下：")
        for n in all_linear_names[:300]:
            print("  ", n)
        raise ValueError(
            "未找到可注入 LoRA 的 Gemma4 文本 Linear 层。"
            "请把 gemma4_linear_modules_debug.txt 或上方 Linear 模块名发给我。"
        )

    print(f"[INFO] 匹配到 {len(matched)} 个文本 LoRA target modules")
    print("[INFO] 前40个 target modules:")
    for n in matched[:40]:
        print("  ", n)

    bad = [n for n in matched if any(k in n.lower() for k in excluded_keywords)]
    if bad:
        print("[ERROR] 匹配到了非文本分支模块，这会导致文本 loss 不连接 LoRA 参数：")
        for n in bad[:40]:
            print("  ", n)
        raise ValueError("LoRA target modules 包含非文本分支，请调整匹配规则。")

    return matched


def print_trainable_parameter_names(model, max_items: int = 50):
    names = []
    for name, p in model.named_parameters():
        if p.requires_grad:
            names.append(name)

    print(f"[INFO] requires_grad=True 参数数量：{len(names)}")
    print("[INFO] 前若干个可训练参数：")
    for n in names[:max_items]:
        print("  ", n)

    if not names:
        raise ValueError("没有任何可训练参数，请检查 LoRA 是否注入成功。")

    # 如果所有可训练参数都在 vision/image 分支，说明注入错位置了
    excluded_keywords = ["vision", "visual", "image", "clip", "projector", "multi_modal", "mm_", "audio", "sound", "speech", "tower"]
    non_vision = [n for n in names if not any(k in n.lower() for k in excluded_keywords)]
    if not non_vision:
        raise ValueError("LoRA 可训练参数全部位于视觉分支，纯文本训练无法产生梯度。")


def write_metric(output_dir: Path, row: Dict[str, Any]):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "metrics_log.jsonl"
    row["timestamp"] = datetime.now().isoformat()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def plot_metrics(output_dir: str):
    try:
        import matplotlib.pyplot as plt
        out = Path(output_dir)
        log_file = out / "metrics_log.jsonl"
        if not log_file.exists():
            return
        rows = [json.loads(line) for line in log_file.open(encoding="utf-8") if line.strip()]
        if not rows:
            return
        df = pd.DataFrame(rows).sort_values("step")
        df.to_csv(out / "metrics.csv", index=False)

        for col in ["loss", "task_loss", "eval_loss", "learning_rate"]:
            if col in df.columns:
                part = df.dropna(subset=[col])
                if not part.empty:
                    plt.figure()
                    plt.plot(part["step"], part[col], marker="o")
                    plt.xlabel("step")
                    plt.ylabel(col)
                    plt.title(f"{col} curve")
                    plt.tight_layout()
                    plt.savefig(out / f"{col}_curve.png", dpi=160)
                    plt.close()
    except Exception as e:
        print(f"[WARN] 绘制训练曲线失败：{e}")


def parse_args():
    parser = argparse.ArgumentParser(description="Gemma4 E2B text-only LoRA 微调脚本")
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--eval_size", type=int, default=1)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--r", type=int, default=4)
    parser.add_argument("--alpha", type=int, default=8)
    parser.add_argument("--target", choices=["attention", "all"], default="attention")
    parser.add_argument("--merge_after_train", action="store_true")
    parser.add_argument("--load_in_8bit", action="store_true", help="Windows 原生环境不建议启用")
    parser.add_argument("--resume_adapter", type=str, default="", help="从已有 LoRA adapter 继续训练，可选")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"模型路径：{args.model_path}")
    print(f"数据路径：{args.dataset}")
    print(f"输出目录：{args.output_dir}")
    print(f"CUDA可用：{torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU：{torch.cuda.get_device_name(0)}")

    print("[INFO] 加载 Gemma4 Processor...")
    processor = AutoProcessor.from_pretrained(
        str(args.model_path),
        trust_remote_code=True,
        use_fast=False,
    )

    # 兼容 processor/tokenizer pad token
    tokenizer = getattr(processor, "tokenizer", None)
    if tokenizer is not None:
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        pad_token_id = tokenizer.pad_token_id
    else:
        pad_token_id = 0

    print("[INFO] 读取并划分数据集...")
    rows = load_jsonl_rows(args.dataset)
    print(f"有效样本数：{len(rows)}")
    if len(rows) < 2:
        raise ValueError("有效训练样本不足。请检查 instruction/output 字段。")

    train_rows, eval_rows = split_rows(rows, args.eval_size)
    print(f"train len: {len(train_rows)}")
    print(f"eval len: {len(eval_rows)}")

    # 打印样例文本，方便确认 chat_template 是否正常
    tmp_ds = JsonlSFTDataset(train_rows[:1], processor, args.max_length)
    sample = tmp_ds._build_text(train_rows[0])
    print("sample text preview:", sample[:500].replace("\n", " "))

    print("[INFO] 加载 Gemma4 模型...")
    model = AutoModelForImageTextToText.from_pretrained(
        str(args.model_path),
        device_map="auto",
        dtype=torch.float16,
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    # 训练时关闭缓存，避免梯度检查/训练兼容问题
    if hasattr(model.config, "use_cache"):
        model.config.use_cache = False

    target_modules = find_gemma4_lora_targets(model, args.target)
    lora_config = LoraConfig(
        r=args.r,
        lora_alpha=args.alpha,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    if args.resume_adapter and Path(args.resume_adapter).exists():
        print(f"[INFO] 从已有 LoRA Adapter 继续训练：{args.resume_adapter}")
        model = PeftModel.from_pretrained(
            model,
            args.resume_adapter,
            is_trainable=True,
        )
    else:
        print("[INFO] 新建 LoRA Adapter")
        model = get_peft_model(model, lora_config)

    model.print_trainable_parameters()
    print_trainable_parameter_names(model)
    model.train()

    train_ds = JsonlSFTDataset(train_rows, processor, args.max_length)
    eval_ds = JsonlSFTDataset(eval_rows, processor, args.max_length)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
    )
    eval_loader = DataLoader(
        eval_ds,
        batch_size=1,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, pad_token_id),
    )

    # 对于 device_map="auto" 模型，优先把输入放到第一个可训练 LoRA 参数所在设备
    first_trainable = next((p for p in model.parameters() if p.requires_grad), None)
    first_device = first_trainable.device if first_trainable is not None else next(model.parameters()).device
    print(f"[INFO] first trainable/input device: {first_device}")

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
    )

    total_update_steps = max(1, math.ceil(len(train_loader) * args.epochs / args.grad_accum))
    global_step = 0
    update_step = 0
    optimizer.zero_grad(set_to_none=True)

    print("[INFO] 开始训练...")
    for epoch in range(int(math.ceil(args.epochs))):
        epoch_loss_sum = 0.0
        micro_steps = 0

        for step, batch in enumerate(train_loader, 1):
            batch = {k: v.to(first_device) for k, v in batch.items()}

            outputs = model(**batch)
            raw_loss = outputs.loss

            if raw_loss is None:
                raise RuntimeError("模型 forward 没有返回 loss，请检查 labels 是否传入。")

            if not raw_loss.requires_grad:
                print("[ERROR] raw_loss.requires_grad=False")
                print("[ERROR] 这通常说明 LoRA 注入到了没有参与文本 forward 的模块，例如 vision/image 分支。")
                print("[ERROR] 请查看上方可训练参数名称，确认是否包含 language/text/model.layers 等文本分支。")
                raise RuntimeError("loss 没有梯度，LoRA 参数没有参与当前文本训练 forward。")

            loss = raw_loss / args.grad_accum
            loss.backward()

            epoch_loss_sum += float(loss.detach().cpu()) * args.grad_accum
            micro_steps += 1
            global_step += 1

            if step % args.grad_accum == 0 or step == len(train_loader):
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                update_step += 1

                lr_now = optimizer.param_groups[0]["lr"]
                train_loss = epoch_loss_sum / max(1, micro_steps)

                metric = {
                    "step": update_step,
                    "split": "train",
                    "loss": train_loss,
                    "task_loss": train_loss,
                    "learning_rate": lr_now,
                    "epoch": epoch + 1,
                }
                print(metric)
                write_metric(output_dir, metric)

                # 每个 update step 后做一次小验证；本地小数据跑通优先
                model.eval()
                eval_losses = []
                with torch.no_grad():
                    for eb in eval_loader:
                        eb = {k: v.to(first_device) for k, v in eb.items()}
                        eout = model(**eb)
                        eval_losses.append(float(eout.loss.detach().cpu()))
                model.train()

                if eval_losses:
                    eval_loss = sum(eval_losses) / len(eval_losses)
                    eval_metric = {
                        "step": update_step,
                        "split": "eval",
                        "eval_loss": eval_loss,
                        "epoch": epoch + 1,
                    }
                    print(eval_metric)
                    write_metric(output_dir, eval_metric)

                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    adapter_dir = output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir)
    try:
        processor.save_pretrained(adapter_dir)
    except Exception as e:
        print(f"[WARN] processor 保存失败：{e}")

    plot_metrics(str(output_dir))
    print(f"Gemma4 LoRA Adapter已保存：{adapter_dir}")

    if args.merge_after_train:
        print("[WARN] Gemma4 本地合并模型显存/内存压力较大，当前脚本暂不自动合并。建议在 AutoDL/Linux 上单独合并。")

    print(f"训练完成：{output_dir}")


if __name__ == "__main__":
    main()
