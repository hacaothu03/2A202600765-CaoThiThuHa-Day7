import os
import json
from src.embeddings import LocalEmbedder
from src.store import EmbeddingStore
from src.chunking import CustomStructuredChunker
from src.models import Document

print("Loading LocalEmbedder (có thể tốn vài giây nếu load model lần đầu)...")
embedder = LocalEmbedder()
store = EmbeddingStore(embedding_fn=embedder)
chunker = CustomStructuredChunker()

files = [
    'data/tthc_ly_lich_tu_phap.json',
    'data/tthc_mo_khoa_dinh_danh.json',
    'data/tthc_dieu_chinh_cu_tru.json',
    'data/tthc_mo_khoa_cccd.json',
    'data/tthc_cap_bhyt.json'
]

docs = []
doc_id = 1
for file in files:
    text = open(file, encoding='utf-8').read()
    chunks = chunker.chunk(text)
    for c in chunks:
        docs.append(Document(id=f"chunk_{doc_id}", content=c))
        doc_id += 1

print(f"Đang nhúng (embed) {len(docs)} chunks vào Vector Store...")
store.add_documents(docs)

queries = [
    "Thời hạn giải quyết thủ tục mở khóa tài khoản định danh điện tử là bao lâu?",
    "Mã thủ tục của Cấp Phiếu Lý lịch tư pháp theo yêu cầu của cơ quan nhà nước là bao nhiêu?",
    "Hồ sơ điều chỉnh thông tin về cư trú trong Cơ sở dữ liệu về cư trú bao gồm những gì?",
    "Mở khóa căn cước điện tử được thực hiện ở cấp nào?",
    "Đối tượng thực hiện thủ tục cấp thẻ bảo hiểm y tế là ai?"
]

print("\n--- KẾT QUẢ CHẠY THẬT TẾ ---")
for i, q in enumerate(queries, 1):
    results = store.search(q, top_k=1)
    print(f"\nCâu hỏi {i}: {q}")
    if results:
        res = results[0]
        chunk_preview = res['content'][:150].replace('\n', ' ') + "..."
        print(f"Top 1 Chunk (Độ chính xác: {res['score']:.3f}): {chunk_preview}")
    else:
        print("Không tìm thấy kết quả.")
