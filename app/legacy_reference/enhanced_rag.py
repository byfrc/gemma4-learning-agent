"""
增强版本地RAG引擎：面向私有垂域知识库的混合检索 + MMR去冗余 + 可解释证据。
依赖尽量保持轻量：pandas / numpy / scikit-learn / joblib。
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


def normalize_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\u200b\ufeff]", "", text)
    return text


def chunk_text(text: str, chunk_size: int = 420, overlap: int = 80) -> List[str]:
    """中文友好的滑窗切块。chunk_size按字符数计算，适合教材/规章/问答类资料。"""
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks, start = [], 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        end = min(len(text), start + chunk_size)
        piece = text[start:end]
        # 尽量在句号/分号/换行处截断，避免语义断裂
        if end < len(text):
            cut = max(piece.rfind("。"), piece.rfind("；"), piece.rfind("\n"))
            if cut > chunk_size * 0.55:
                end = start + cut + 1
                piece = text[start:end]
        chunks.append(piece.strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


class HybridRAGEngine:
    """本地混合检索：word TF-IDF + char TF-IDF + MMR。

    - word/ngram负责关键词和术语；char/ngram负责中文短语、错别字、近似匹配。
    - MMR避免返回重复段落，提高上下文覆盖度。
    """

    def __init__(self, model_path: str | Path = "models/hybrid_rag.joblib"):
        self.model_path = Path(model_path)
        self.word_vectorizer: Optional[TfidfVectorizer] = None
        self.char_vectorizer: Optional[TfidfVectorizer] = None
        self.word_matrix = None
        self.char_matrix = None
        self.chunks: List[Dict[str, Any]] = []

    def build_from_dataframe(
        self,
        df: pd.DataFrame,
        text_columns: Optional[List[str]] = None,
        metadata_columns: Optional[List[str]] = None,
        chunk_size: int = 420,
        overlap: int = 80,
    ) -> Dict[str, Any]:
        if df.empty:
            raise ValueError("数据为空，无法构建知识库")

        if text_columns is None:
            # 自动选择常见字段；没有则拼接所有object列
            candidates = ["content", "text", "answer", "question", "title", "chapter", "course"]
            text_columns = [c for c in candidates if c in df.columns]
            if not text_columns:
                text_columns = [c for c in df.columns if df[c].dtype == "object"]
        if metadata_columns is None:
            metadata_columns = [c for c in ["doc_id", "course", "chapter", "title", "source", "difficulty"] if c in df.columns]

        rows = []
        for i, row in df.iterrows():
            doc_id = str(row.get("doc_id", f"doc_{i}"))
            text = "\n".join(normalize_text(row.get(c, "")) for c in text_columns if normalize_text(row.get(c, "")))
            metadata = {c: row.get(c, "") for c in metadata_columns}
            for j, chunk in enumerate(chunk_text(text, chunk_size=chunk_size, overlap=overlap)):
                rows.append({
                    "chunk_id": f"{doc_id}_chunk_{j}",
                    "doc_id": doc_id,
                    "text": chunk,
                    "metadata": metadata,
                })
        if not rows:
            raise ValueError("没有可用文本，无法构建知识库")

        self.chunks = rows
        corpus = [r["text"] for r in rows]
        self.word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, max_df=0.95)
        self.char_vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=1, max_df=0.95)
        self.word_matrix = self.word_vectorizer.fit_transform(corpus)
        self.char_matrix = self.char_vectorizer.fit_transform(corpus)
        self.save()
        return {"chunks": len(self.chunks), "features_word": self.word_matrix.shape[1], "features_char": self.char_matrix.shape[1]}

    def save(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "word_vectorizer": self.word_vectorizer,
            "char_vectorizer": self.char_vectorizer,
            "word_matrix": self.word_matrix,
            "char_matrix": self.char_matrix,
            "chunks": self.chunks,
        }, self.model_path)

    def load(self) -> bool:
        if not self.model_path.exists():
            return False
        obj = joblib.load(self.model_path)
        self.word_vectorizer = obj["word_vectorizer"]
        self.char_vectorizer = obj["char_vectorizer"]
        self.word_matrix = obj["word_matrix"]
        self.char_matrix = obj["char_matrix"]
        self.chunks = obj["chunks"]
        return True

    def ready(self) -> bool:
        return self.word_vectorizer is not None and self.char_vectorizer is not None and len(self.chunks) > 0

    def _scores(self, query: str, word_weight: float = 0.45, char_weight: float = 0.55) -> np.ndarray:
        if not self.ready():
            return np.array([])
        q_word = self.word_vectorizer.transform([query])
        q_char = self.char_vectorizer.transform([query])
        s_word = cosine_similarity(q_word, self.word_matrix)[0]
        s_char = cosine_similarity(q_char, self.char_matrix)[0]
        return word_weight * s_word + char_weight * s_char

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        candidate_k: int = 30,
        min_score: float = 0.03,
        mmr_lambda: float = 0.72,
        metadata_filter: Optional[Dict[str, str]] = None,
    ) -> List[RetrievedChunk]:
        query = normalize_text(query)
        if not query or not self.ready():
            return []
        scores = self._scores(query)
        if scores.size == 0:
            return []

        # 元数据过滤：如 course/chapter/difficulty
        valid = np.ones(len(self.chunks), dtype=bool)
        if metadata_filter:
            for key, val in metadata_filter.items():
                if val:
                    valid &= np.array([str(c.get("metadata", {}).get(key, "")) == str(val) for c in self.chunks])
        scores = np.where(valid, scores, -1)

        cand = [int(i) for i in np.argsort(scores)[::-1][:candidate_k] if scores[i] >= min_score]
        if not cand:
            return []

        # MMR：优先相关，同时避免相互高度重复
        selected: List[int] = []
        char_sub = self.char_matrix[cand]
        sim_between = cosine_similarity(char_sub)
        while cand and len(selected) < top_k:
            if not selected:
                best_local = 0
            else:
                selected_locals = [original_cand.index(i) for i in selected] if False else None
                best_local, best_val = None, -1e9
                for local_i, idx in enumerate(cand):
                    selected_positions = [original_candidates.index(s) for s in selected]
                    redundancy = max(sim_between[local_i, p] for p in selected_positions) if selected_positions else 0
                    val = mmr_lambda * scores[idx] - (1 - mmr_lambda) * redundancy
                    if val > best_val:
                        best_local, best_val = local_i, val
            if not selected:
                original_candidates = cand.copy()
            idx = cand.pop(best_local)
            selected.append(idx)

        return [RetrievedChunk(
            chunk_id=self.chunks[i]["chunk_id"],
            doc_id=self.chunks[i]["doc_id"],
            text=self.chunks[i]["text"],
            score=float(scores[i]),
            metadata=self.chunks[i].get("metadata", {}),
        ) for i in selected]

    def build_prompt(self, query: str, docs: List[RetrievedChunk], role: str = "你是一名严谨的教育领域AI助教") -> str:
        evidence = "\n\n".join(
            f"[证据{i+1} | score={d.score:.3f} | doc={d.doc_id}]\n{d.text}" for i, d in enumerate(docs)
        )
        return f"""{role}。请严格优先基于证据回答；证据不足时要说明不确定，并给出下一步学习/检索建议。

【检索证据】
{evidence if evidence else '无'}

【用户问题】
{query}

【回答要求】
1. 先给直接结论；
2. 再分点解释依据；
3. 最后给学习建议或下一步问题；
4. 不要编造证据中不存在的具体数据。"""


import io


def _safe_read_csv_from_bytes(raw: bytes) -> pd.DataFrame:
    """
    尝试用多种常见编码读取 CSV，兼容 UTF-8、UTF-8-SIG、GBK。
    """
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]

    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except Exception as e:
            last_error = e

    raise ValueError(f"CSV 文件读取失败，可能是编码或格式问题：{last_error}")


def _safe_decode_text(raw: bytes) -> str:
    """
    尝试用多种编码读取 TXT / MD。
    """
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]

    for enc in encodings:
        try:
            return raw.decode(enc)
        except Exception:
            continue

    return raw.decode("utf-8", errors="ignore")


def _csv_dataframe_to_knowledge_rows(df: pd.DataFrame, file_name: str) -> list[dict]:
    """
    将一个 CSV 转成 RAG 知识记录。

    处理逻辑：
    - 每一行作为一条知识记录；
    - 将每个非空字段拼成 “列名：值”；
    - 保留 source_file、row_index 等元信息，方便检索时展示来源。
    """
    rows = []

    if df.empty:
        return rows

    # 清理列名
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for idx, row in df.iterrows():
        parts = []

        for col in df.columns:
            value = row.get(col, "")

            if pd.isna(value):
                continue

            value = str(value).strip()
            if not value:
                continue

            parts.append(f"{col}：{value}")

        content = "；".join(parts).strip()

        if not content:
            continue

        rows.append({
            "doc_id": f"{Path(file_name).stem}_row_{idx}",
            "content": content,
            "source_file": file_name,
            "file_type": "csv",
            "row_index": int(idx),
            "title": Path(file_name).stem
        })

    return rows


def _text_file_to_knowledge_row(text: str, file_name: str, file_type: str) -> list[dict]:
    """
    将 TXT / MD 文件转成 RAG 知识记录。

    处理逻辑：
    - 每个文件先作为一篇完整文档；
    - 后续 build_from_dataframe 会根据 chunk_size / overlap 自动切块。
    """
    text = normalize_text(text)

    if not text:
        return []

    return [{
        "doc_id": Path(file_name).stem,
        "content": text,
        "source_file": file_name,
        "file_type": file_type,
        "row_index": "",
        "title": Path(file_name).stem
    }]


def load_uploaded_knowledge_files(uploaded_files) -> pd.DataFrame:
    """
    批量读取 Streamlit 上传的多个 CSV / TXT / MD 文件。

    返回统一格式 DataFrame：
    - doc_id
    - content
    - source_file
    - file_type
    - row_index
    - title
    """
    if not uploaded_files:
        return pd.DataFrame(columns=[
            "doc_id",
            "content",
            "source_file",
            "file_type",
            "row_index",
            "title"
        ])

    all_rows = []

    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        suffix = Path(file_name).suffix.lower().replace(".", "")

        # 重要：每次读取前移动到文件开头，避免 Streamlit 缓存导致读取为空
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        raw = uploaded_file.read()

        if suffix == "csv":
            df = _safe_read_csv_from_bytes(raw)
            rows = _csv_dataframe_to_knowledge_rows(df, file_name)
            all_rows.extend(rows)

        elif suffix in ["txt", "md"]:
            text = _safe_decode_text(raw)
            rows = _text_file_to_knowledge_row(text, file_name, suffix)
            all_rows.extend(rows)

        else:
            # 理论上 file_uploader 已经过滤，这里只是兜底
            continue

    result = pd.DataFrame(all_rows)

    if result.empty:
        return pd.DataFrame(columns=[
            "doc_id",
            "content",
            "source_file",
            "file_type",
            "row_index",
            "title"
        ])

    return result


def load_csv_or_txt(uploaded_file) -> pd.DataFrame:
    """
    兼容旧代码：单文件读取。
    如果旧页面还在调用 load_csv_or_txt，也不会报错。
    """
    return load_uploaded_knowledge_files([uploaded_file])
