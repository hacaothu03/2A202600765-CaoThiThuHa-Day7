# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Cao Thị Thu Hà
**Mã học viên:** 2A202600765
**Nhóm:** C6
**Ngày:** 5/6/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> Hai vector đại diện cho hai đoạn văn bản có góc hợp nhau rất nhỏ trong không gian đa chiều, cho thấy chúng mang ý nghĩa ngữ nghĩa gần giống nhau, dù có thể dùng từ ngữ khác nhau.

**Ví dụ HIGH similarity:**
- Sentence A: "Hướng dẫn đăng ký tài khoản định danh điện tử mức độ 2."
- Sentence B: "Cách tạo tài khoản VNeID xác thực bằng sinh trắc học."
- Tại sao tương đồng: Cả hai đều nói về quá trình đăng ký/tạo tài khoản định danh điện tử, các khái niệm cốt lõi giống nhau nên embedding sẽ gần nhau trong không gian vector.

**Ví dụ LOW similarity:**
- Sentence A: "Hướng dẫn đăng ký tài khoản định danh điện tử mức độ 2."
- Sentence B: "Thời tiết Hà Nội hôm nay nhiều mây, có mưa rào."
- Tại sao khác: Hoàn toàn khác chủ đề (hành chính điện tử so với thời tiết), không có điểm chung về ngữ nghĩa lẫn từ vựng.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity đo góc giữa hai vector, bỏ qua độ lớn (magnitude), do đó không bị ảnh hưởng bởi độ dài của văn bản. Một văn bản dài và một văn bản ngắn cùng chủ đề sẽ có cosine similarity cao dù vector của chúng có độ lớn rất khác nhau. Euclidean distance lại bị tác động bởi độ lớn vector, dễ đánh giá sai mức độ tương đồng ngữ nghĩa thực sự.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = 23`
> *Đáp án:* 23 chunks.

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> Số lượng chunks tăng lên 25 (`ceil(9900 / 400)`). Tăng overlap giúp đảm bảo ngữ cảnh ở ranh giới giữa các chunk không bị mất đi — khi retrieval truy vấn một đoạn thông tin nằm ở "vùng giao" giữa hai chunk, overlap lớn hơn giúp ít nhất một chunk vẫn bao phủ trọn vẹn thông tin đó.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Tư vấn thủ tục hành chính công Việt Nam

**Tại sao nhóm chọn domain này?**
> Thủ tục hành chính công là lĩnh vực chứa nhiều tài liệu có cấu trúc rõ ràng (mã thủ tục, trình tự thực hiện, thành phần hồ sơ, thời hạn giải quyết…), rất phù hợp để thử nghiệm nhiều chiến lược chunking khác nhau. Đây cũng là domain có giá trị thực tiễn cao, giúp người dân tra cứu thủ tục nhanh chóng mà không phải đọc toàn bộ văn bản pháp lý dài.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------| 
| 1 | `tthc_ly_lich_tu_phap.json` | Cổng DVC | ~2500 | `{"type": "tthc", "ma_thu_tuc": "3.000331"}` |
| 2 | `tthc_mo_khoa_dinh_danh.json` | Cổng DVC | ~1800 | `{"type": "tthc", "ma_thu_tuc": "1.000124"}` |
| 3 | `tthc_dieu_chinh_cu_tru.json` | Cổng DVC | ~2100 | `{"type": "tthc", "ma_thu_tuc": "2.000456"}` |
| 4 | `tthc_mo_khoa_cccd.json` | Cổng DVC | ~1900 | `{"type": "tthc", "ma_thu_tuc": "1.000789"}` |
| 5 | `tthc_cap_bhyt.json` | Cổng DVC | ~2200 | `{"type": "tthc", "ma_thu_tuc": "4.000112"}` |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `type` | string | `tthc`, `faq` | Phân loại luồng tra cứu, giúp `search_with_filter` chỉ tìm kiếm trong đúng loại tài liệu, tránh kết quả lạc đề. |
| `ma_thu_tuc` | string | `3.000331` | Định danh duy nhất cho từng thủ tục, hỗ trợ filter chính xác khi người dùng hỏi về một thủ tục cụ thể. |
| `url` | string | `https://...` | Cung cấp nguồn tham chiếu gốc để agent có thể trích dẫn (grounding) và người dùng tự kiểm chứng thông tin. |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu dạng chuỗi JSON thô:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| `tthc_ly_lich` | FixedSizeChunker (`fixed_size`) | 8 | 300.0 | Phá vỡ hoàn toàn cấu trúc JSON |
| `tthc_ly_lich` | SentenceChunker (`by_sentences`) | 12 | 210.5 | Cắt ngẫu nhiên tại các dấu chấm trong Value |
| `tthc_ly_lich` | RecursiveChunker (`recursive`) | 6 | 400.2 | Khá hơn nhưng vẫn hay cắt giữa các trường Key-Value |

### Strategy Của Tôi

**Loại:** RecursiveChunker (tham số tối ưu)

**Mô tả cách hoạt động:**
> RecursiveChunker thử cắt văn bản theo danh sách separator theo thứ tự ưu tiên: `\n\n` → `\n` → `. ` → ` `. Nếu đoạn sau khi cắt vẫn vượt `chunk_size`, hàm đệ quy tiếp với separator cấp dưới. Tôi tinh chỉnh tham số `chunk_size=450, chunk_overlap=80` và đặt separator đầu tiên là `\n` (ranh giới dòng trong JSON đã được flatten) để tránh cắt giữa một trường Key-Value.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Dữ liệu thủ tục hành chính sau khi flatten từ JSON sang text có cấu trúc dòng-dòng rõ ràng (mỗi trường một dòng). RecursiveChunker với separator `\n` ưu tiên sẽ cắt ở ranh giới dòng trước, giữ nguyên cặp Key-Value. Khi cần cắt nhỏ hơn mới dùng dấu chấm hoặc khoảng trắng. Điều này cân bằng giữa tính đơn giản (không cần custom code) và chất lượng chunk tốt hơn FixedSizeChunker hay SentenceChunker.

**Code snippet (cấu hình sử dụng):**
```python
chunker = RecursiveChunker(
    chunk_size=450,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = chunker.chunk(flattened_text)
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------| 
| `tthc_ly_lich` | best baseline (`fixed_size`) | 8 | 300 | Kém, cắt giữa câu gây mất ngữ cảnh |
| `tthc_ly_lich` | **của tôi (`recursive`, chunk_size=450)** | 6 | 400 | Tốt, ít cắt giữa trường dữ liệu quan trọng |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Huy | Custom Structured Chunker | 9/10 | Tối ưu kích thước chunk, chống phân mảnh | Phải hardcode danh sách các trường gộp/tách |
| Tôi (Hà) | RecursiveChunker | 7/10 | Không cần code hàm riêng, dễ tái sử dụng | Cắt vỡ các dấu ngoặc nhọn `{}` của JSON nếu không flatten trước |
| Thảo | SentenceChunker | 6/10 | Giữ được trọn vẹn ngữ nghĩa của từng câu | File JSON hiếm khi dùng dấu chấm để kết câu, dẫn đến cắt sai hoặc tạo ra chunk quá lớn |
| Kiên | FixedSizeChunker | 5/10 | Tốc độ cắt nhanh | Làm mất hoàn toàn ngữ cảnh (context) |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> Custom Structured Chunker (của Huy) cho kết quả tốt nhất vì chủ động hiểu schema dữ liệu để "gộp trường nhỏ, tách trường lớn". RecursiveChunker của tôi đạt điểm trung bình tốt khi đã flatten JSON thành text, nhưng vẫn kém linh hoạt hơn so với custom chunker vì không phân biệt được trường quan trọng và không quan trọng. Với domain có cấu trúc tường minh như hành chính công, việc đầu tư viết custom chunker cho kết quả retrieval đáng kể hơn.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Dùng `re.split` với pattern `(?<=[.!?])\s+` để tách câu tại các dấu câu kết câu. Sau khi làm sạch chuỗi rỗng, gom các câu lại thành chunk theo giới hạn `max_sentences_per_chunk`. Mỗi chunk có ít nhất 1 câu, loại bỏ khoảng trắng thừa ở đầu và cuối.

**`RecursiveChunker.chunk` / `_split`** — approach:
> Triển khai đệ quy: Nếu độ dài văn bản ≤ `chunk_size` thì trả về ngay. Nếu vượt, thử cắt bằng separator đầu tiên trong danh sách. Với mỗi đoạn thu được, nếu vẫn còn quá dài, đệ quy cắt lại bằng separator tiếp theo (cấp thấp hơn). Các chunk nhỏ được ghép lại có tính đến `chunk_overlap` để bảo toàn ngữ cảnh biên.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> Lưu trữ in-memory dưới dạng `list[dict]` với các trường `id`, `text`, `embedding`, `metadata`. Hàm `search` gọi embedder trên câu query, tính cosine similarity bằng dot product (sau khi normalize), sắp xếp giảm dần và trả về top_k kết quả.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter` trước tiên lọc `self._store` để chỉ giữ lại các document có metadata khớp với `metadata_filter`, sau đó tính similarity trên tập đã lọc và trả về top_k. `delete_document` dùng list comprehension để loại bỏ tất cả entry có `doc_id` trùng khớp, trả về `True` nếu tìm thấy và xóa thành công.

### KnowledgeBaseAgent

**`answer`** — approach:
> Gọi `store.search(question, top_k=3)` để lấy các chunk liên quan nhất. Nối các chunk thành `context` (ngăn cách bởi `\n---\n`). Tạo prompt theo format: `Dựa vào thông tin sau:\n{context}\n\nTrả lời câu hỏi: {question}`. Gửi prompt tới LLM và trả về câu trả lời. Nếu không tìm thấy chunk liên quan, trả về thông báo không đủ thông tin.

### Test Results

```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0
collected 42 items

tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_empty_input PASSED
tests/test_solution.py::TestRecursiveChunker::test_basic_split PASSED
tests/test_solution.py::TestRecursiveChunker::test_overlap_preserved PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_and_search PASSED
tests/test_solution.py::TestEmbeddingStore::test_get_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreFilter::test_filter_by_metadata PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
...
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_uses_context PASSED [100%]

============================= 42 passed in 2.35s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Thủ tục cấp phiếu lý lịch tư pháp | Hồ sơ xin cấp lý lịch tư pháp gồm những gì? | high | 0.8320 | Có |
| 2 | Thủ tục cấp phiếu lý lịch tư pháp | Cách nấu món phở bò truyền thống | low | 0.0085 | Có |
| 3 | Mở khóa tài khoản định danh điện tử | Kích hoạt lại VNeID bị khóa | high | 0.7950 | Có |
| 4 | Đăng ký thường trú tại địa phương mới | Công thức tính diện tích hình thang | low | -0.0230 | Có |
| 5 | Thành phần hồ sơ điều chỉnh thông tin cư trú | Giấy tờ cần thiết để thay đổi nơi ở đăng ký | high | 0.8610 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Bất ngờ nhất là Pair 3: "Mở khóa tài khoản định danh điện tử" và "Kích hoạt lại VNeID bị khóa" dùng hoàn toàn khác từ ngữ nhưng điểm tương đồng vẫn đạt 0.7950. Điều này cho thấy embedding không chỉ so khớp từ khóa mà thực sự biểu diễn không gian ngữ nghĩa — "mở khóa/kích hoạt lại" và "VNeID/tài khoản định danh" được mô hình hiểu là các khái niệm tương đương trong cùng một ngữ cảnh hành chính điện tử.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của tôi trong package `src`. **5 queries trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | Thời hạn giải quyết thủ tục mở khóa tài khoản định danh điện tử là bao lâu? | 03 Ngày làm việc. |
| 2 | Mã thủ tục của "Cấp Phiếu Lý lịch tư pháp theo yêu cầu của cơ quan nhà nước" là bao nhiêu? | Mã thủ tục là 3.000331, do Cấp Bộ (Cục Hồ sơ nghiệp vụ) thực hiện. |
| 3 | Hồ sơ điều chỉnh thông tin về cư trú trong Cơ sở dữ liệu về cư trú bao gồm những gì? | Bao gồm Tờ khai thay đổi thông tin cư trú (Mẫu CT01) và Giấy tờ chứng minh việc điều chỉnh. |
| 4 | Mở khóa căn cước điện tử được thực hiện ở cấp nào? | Thực hiện tại Cấp Tỉnh (Phòng cảnh sát quản lý hành chính về trật tự xã hội, Công an tỉnh). |
| 5 | Đối tượng thực hiện thủ tục cấp thẻ bảo hiểm y tế là ai? | Công dân Việt Nam; Cán bộ, công chức, viên chức. |

### Kết Quả Của Tôi (Chạy thật với LocalEmbedder `all-MiniLM-L6-v2`, RecursiveChunker chunk_size=450)

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Thời hạn mở khóa tài khoản định danh... | "Mở khóa tài khoản định danh... Thời hạn: 03 Ngày làm việc..." | 0.741 | Có | Thời hạn là 03 Ngày làm việc. |
| 2 | Mã thủ tục Phiếu LLTP... | "Cấp Phiếu Lý lịch tư pháp... Mã thủ tục: 3.000331, Cấp Bộ..." | 0.798 | Có | Mã thủ tục 3.000331, do Cấp Bộ thực hiện. |
| 3 | Hồ sơ điều chỉnh cư trú... | "Điều chỉnh thông tin cư trú... Thành phần hồ sơ: Tờ khai CT01, Giấy tờ chứng minh..." | 0.812 | Có | Gồm Tờ khai CT01 và giấy tờ chứng minh. |
| 4 | Mở khóa căn cước ở cấp nào... | "Mở khóa căn cước... Cấp thực hiện: Cấp Tỉnh, Công an tỉnh..." | 0.823 | Có | Thực hiện tại Cấp Tỉnh, Phòng cảnh sát quản lý hành chính. |
| 5 | Đối tượng cấp thẻ BHYT... | "Cấp thẻ bảo hiểm y tế... Đối tượng: Công dân Việt Nam, cán bộ công chức..." | 0.857 | Có | Là Công dân Việt Nam, Cán bộ, công chức, viên chức. |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

**Failure Case (Exercise 3.5):**
> Query 1 có score thấp nhất (0.741) vì RecursiveChunker đôi khi cắt cụm "Thời hạn giải quyết: 03 Ngày làm việc" vào một chunk riêng, tách rời khỏi tên thủ tục. Kết quả top-1 vẫn đúng nhưng kém tự tin hơn so với Custom Structured Chunker của Huy (0.765). Để cải thiện: cần thêm tên thủ tục vào đầu mỗi chunk (prefix injection) tương tự như cách Custom Structured Chunker đã làm.

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Từ Huy (Custom Structured Chunker): Việc chủ động hiểu schema tài liệu để thiết kế chunking strategy riêng thay vì dùng chiến lược chung chung mang lại cải thiện rõ rệt về retrieval quality. Cụ thể, prefix injection (gắn tên thủ tục vào đầu mỗi chunk) giúp mô hình luôn biết chunk đang nói về thủ tục nào, tránh nhầm lẫn khi các thủ tục có từ ngữ tương tự nhau.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Metadata filtering có thể kết hợp với vector search theo kiểu "pre-filter then search" (lọc metadata trước, sau đó tìm kiếm trong tập đã lọc) thay vì search toàn bộ rồi filter. Cách này không chỉ tăng độ chính xác mà còn giảm chi phí tính toán đáng kể khi tập dữ liệu lớn. Nhóm bạn minh họa rõ trường hợp filter theo `ma_thu_tuc` loại bỏ hoàn toàn hallucination khi agent trả lời về một thủ tục cụ thể.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Tôi sẽ thực hiện bước pre-processing kỹ hơn: chuyển JSON thành văn bản thuần túy theo format có cấu trúc rõ ràng (ví dụ: `[Tên thủ tục]\nLĩnh vực: ...\nTrình tự: Bước 1...`) trước khi đưa vào RecursiveChunker. Bước này giúp separator `\n` hoạt động hiệu quả hơn và chunk output sẽ sạch hơn, không còn dấu ngoặc `{}` hay dấu `"` của JSON gây nhiễu embedding. Ngoài ra, sẽ thêm prefix injection như của Huy để duy trì ngữ cảnh thủ tục trong mỗi chunk.

---
