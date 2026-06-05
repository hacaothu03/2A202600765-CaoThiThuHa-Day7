from __future__ import annotations

import json
import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        
        parts = re.split(r'(\. |\! |\? |\.\n)', text)
        sentences = []
        for i in range(0, len(parts), 2):
            sentence = parts[i]
            if i + 1 < len(parts):
                sentence += parts[i + 1]
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
                
        chunks = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            chunks.append(" ".join(sentences[i:i + self.max_sentences_per_chunk]))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]
            
        if not remaining_separators:
            chunks = []
            for i in range(0, len(current_text), self.chunk_size):
                chunks.append(current_text[i:i + self.chunk_size])
            return chunks

        sep = remaining_separators[0]
        next_separators = remaining_separators[1:]
        
        if sep == "":
            parts = list(current_text)
        else:
            parts = current_text.split(sep)
            
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if current_chunk:
                attempt = current_chunk + sep + part
            else:
                attempt = part
                
            if len(attempt) <= self.chunk_size:
                current_chunk = attempt
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
                
        if current_chunk:
            chunks.append(current_chunk)
            
        final_chunks = []
        for c in chunks:
            if len(c) > self.chunk_size:
                final_chunks.extend(self._split(c, next_separators))
            else:
                final_chunks.append(c)
                
        return final_chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot_product = _dot(vec_a, vec_b)
    mag_a = math.sqrt(_dot(vec_a, vec_a))
    mag_b = math.sqrt(_dot(vec_b, vec_b))
    
    if mag_a == 0 or mag_b == 0:
        return 0.0
        
    return dot_product / (mag_a * mag_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        fixed_chunks = FixedSizeChunker(chunk_size=chunk_size).chunk(text)
        sentence_chunks = SentenceChunker(max_sentences_per_chunk=3).chunk(text)
        recursive_chunks = RecursiveChunker(chunk_size=chunk_size).chunk(text)

        def get_stats(chunks):
            return {
                "count": len(chunks),
                "avg_length": sum(len(c) for c in chunks) / len(chunks) if chunks else 0,
                "chunks": chunks
            }

        return {
            "fixed_size": get_stats(fixed_chunks),
            "by_sentences": get_stats(sentence_chunks),
            "recursive": get_stats(recursive_chunks)
        }


class CustomStructuredChunker:
    """
    Custom strategy for crawling DVC JSON data.
    Groups small fields together, and splits large fields into individual chunks.
    """

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
            
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback to simple splitting if not valid JSON
            return RecursiveChunker().chunk(text)

        chunks = []
        doc_type = data.get("type", "")
        
        if doc_type == "faq":
            chunks.append(f"Câu hỏi: {data.get('title', '')}\nTrả lời: {data.get('answer', '')}")
            
        elif doc_type == "tthc" or "Tên thủ tục" in data:
            name = f"Thủ tục: {data.get('Tên thủ tục', '')}\n"
            
            # Gộp các trường bé thành 1 chunk chung để không bị phân mảnh
            small_fields = ["Mã thủ tục", "Lĩnh vực", "Cấp thực hiện", "Cơ quan thực hiện", "Kết quả thực hiện"]
            small_values = []
            for k in small_fields:
                if k in data and data[k]:
                    small_values.append(f"{k}: {data[k]}")
                    
            if small_values:
                chunks.append(name + "Thông tin chung: " + ", ".join(small_values))
            
            # Tách các trường to, quan trọng thành các chunk riêng biệt
            large_fields = ["Trình tự thực hiện", "Cách thức thực hiện", "Thành phần hồ sơ", "Yêu cầu, điều kiện thực hiện"]
            for key in large_fields:
                if key in data and data[key]:
                    chunks.append(name + f"{key}: {data[key]}")
                    
        elif doc_type == "vbqppl":
            name = f"Văn bản: {data.get('Tên văn bản', '')}\n"
            content = data.get("Nội dung", "")
            # Dùng recursive chunker cho nội dung dài
            content_chunks = RecursiveChunker(chunk_size=300).chunk(content)
            for c in content_chunks:
                chunks.append(name + c)
                
        else:
            # Nếu không nhận diện được type, convert dict sang string và recursive
            chunks = RecursiveChunker().chunk(str(data))
            
        return chunks
