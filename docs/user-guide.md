# Memgrap — Hướng dẫn sử dụng

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Yêu cầu hệ thống](#2-yêu-cầu-hệ-thống)
3. [Cài đặt](#3-cài-đặt)
4. [Xác nhận hoạt động](#4-xác-nhận-hoạt-động)
5. [Cách sử dụng](#5-cách-sử-dụng)
6. [Dashboard](#6-dashboard)
7. [Cấu hình nâng cao](#7-cấu-hình-nâng-cao)
8. [Xử lý sự cố](#8-xử-lý-sự-cố)
9. [FAQ](#9-faq)

---

## 1. Giới thiệu

Memgrap là hệ thống **bộ nhớ dài hạn** cho Claude Code, giúp Claude ghi nhớ các quyết định, mẫu code, và ngữ cảnh dự án qua nhiều phiên làm việc. Thay vì mất toàn bộ ngữ cảnh mỗi lần đóng Claude Code, Memgrap lưu trữ thông tin dưới dạng **đồ thị tri thức có thời gian** (temporal knowledge graph) — nghĩa là nó không chỉ nhớ "cái gì" mà còn nhớ "khi nào" và "liên quan đến gì".

Memgrap kết nối tự động với Claude Code thông qua giao thức MCP (Model Context Protocol), nên bạn không cần thao tác gì thêm sau khi cài đặt.

---

## 2. Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|------------|----------|
| **Python** | Phiên bản 3.10 trở lên |
| **Docker Desktop** | Đang chạy (dùng để khởi động Neo4j database) |
| **OpenAI API Key** | Cần để trích xuất thực thể và tạo vector nhúng |
| **Claude Code** | Đã cài đặt và hoạt động |

### Kiểm tra trước khi cài đặt

Mở terminal và chạy:

```bash
python --version    # Cần hiển thị 3.10 trở lên
docker --version    # Cần hiển thị phiên bản Docker
```

Nếu chưa cài:
- Python: tải tại [python.org](https://python.org)
- Docker Desktop: tải tại [docker.com](https://docker.com)
- OpenAI API Key: tạo tại [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

## 3. Cài đặt

Memgrap cung cấp script cài đặt tự động. Bạn chỉ cần chạy một lệnh duy nhất.

### Windows

1. Mở terminal (Command Prompt hoặc PowerShell) tại thư mục Memgrap
2. Chạy:

```bash
setup.bat
```

3. Khi được hỏi "Enter OpenAI API key", nhập API key của bạn (bắt đầu bằng `sk-...`)
4. Đợi script hoàn tất (khoảng 1-2 phút)

### macOS / Linux

1. Mở terminal tại thư mục Memgrap
2. Chạy:

```bash
chmod +x setup.sh
./setup.sh
```

3. Nhập OpenAI API key khi được hỏi
4. Đợi script hoàn tất

### Script cài đặt làm gì?

Script tự động thực hiện 6 bước:

| Bước | Hành động |
|------|-----------|
| 1/6 | Kiểm tra Python và Docker đã cài chưa |
| 2/6 | Cài đặt thư viện Python (Graphiti, FastMCP, v.v.) |
| 3/6 | Khởi động Neo4j database trong Docker |
| 4/6 | Tạo file `.env` và lưu OpenAI API key |
| 5/6 | Cấu hình MCP để Claude Code nhận diện Memgrap |
| 6/6 | Kiểm tra kết nối |

### Bước cuối cùng: Khởi động lại Claude Code

Sau khi script hoàn tất, **đóng và mở lại Claude Code**. Claude Code sẽ tự động nhận diện Memgrap thông qua file `.mcp.json`.

---

## 4. Xác nhận hoạt động

Sau khi khởi động lại Claude Code, hãy kiểm tra Memgrap đã kết nối chưa bằng cách gõ vào Claude Code:

```
Hãy gọi get_status để kiểm tra Memgrap
```

Claude Code sẽ gọi tool `get_status` và trả về kết quả tương tự:

```json
{
  "status": "connected",
  "neo4j": "bolt://localhost:7687",
  "initialized": true,
  "group_id": "default"
}
```

**Nếu kết quả hiển thị `"status": "connected"`** — Memgrap đã hoạt động, bạn có thể bắt đầu sử dụng.

**Nếu gặp lỗi** — xem phần [Xử lý sự cố](#8-xử-lý-sự-cố).

Bạn cũng có thể kiểm tra Neo4j trực tiếp qua trình duyệt:
- Mở [http://localhost:7474](http://localhost:7474)
- Đăng nhập: username `neo4j`, password `password`

---

## 5. Cách sử dụng

Memgrap cung cấp **7 công cụ (tools)** mà Claude Code có thể sử dụng. Bạn không cần gọi trực tiếp — chỉ cần nói chuyện bình thường với Claude Code, hệ thống sẽ tự gọi tool phù hợp.

### 5.1. `remember` — Lưu thông tin

**Mục đích:** Lưu quyết định, mẫu code, ngữ cảnh dự án vào đồ thị tri thức.

**Cách dùng:** Nói với Claude Code điều bạn muốn ghi nhớ.

**Ví dụ:**

```
Hãy nhớ rằng chúng ta chọn PostgreSQL cho database vì cần hỗ trợ JSON
và full-text search. Quyết định này được đưa ra trong sprint 3.
```

Claude Code sẽ gọi `remember` và Memgrap tự động:
- Trích xuất thực thể: `PostgreSQL`, `Sprint 3`
- Tạo mối quan hệ: "PostgreSQL được chọn làm database"
- Gán nhãn thời gian cho sự kiện

**Các loại thông tin nên lưu:**
- Quyết định kỹ thuật (ví dụ: "Chọn React thay vì Vue")
- Mẫu code quan trọng (ví dụ: "Dùng Repository pattern cho data layer")
- Ngữ cảnh dự án (ví dụ: "Deadline giao hàng là ngày 15/4")
- Thông tin bug (ví dụ: "API timeout khi payload > 5MB")
- Sở thích người dùng (ví dụ: "Khách hàng muốn giao diện dark mode")

### 5.2. `recall` — Tìm kiếm thông tin đã lưu

**Mục đích:** Tìm lại thông tin liên quan từ bộ nhớ bằng ngôn ngữ tự nhiên.

**Cách dùng:** Hỏi Claude Code về thông tin bạn đã lưu trước đó.

**Ví dụ:**

```
Chúng ta đã quyết định dùng database gì?
```

```
Nhắc lại lý do chọn kiến trúc microservices?
```

```
Có thông tin gì về authentication không?
```

Memgrap sử dụng **tìm kiếm ngữ nghĩa** (semantic search) — nghĩa là bạn không cần nhớ chính xác từ khóa, chỉ cần mô tả ý bạn muốn tìm.

Kết quả trả về bao gồm:
- **Sự kiện/mối quan hệ** giữa các thực thể
- **Thời gian** — khi nào thông tin được ghi nhận
- **Độ liên quan** — sắp xếp theo mức độ phù hợp

### 5.3. `understand_code` — Tìm kiếm thực thể code

**Mục đích:** Tìm các thực thể liên quan đến code: mẫu thiết kế, thư viện, công cụ, quyết định kỹ thuật.

**Cách dùng:**

```
Tìm các pattern liên quan đến authentication trong dự án
```

```
Có những thư viện nào đang được sử dụng cho API?
```

Khác với `recall` (trả về mối quan hệ), `understand_code` trả về **các thực thể** (entity nodes) với tên, mô tả tóm tắt, và nhãn phân loại.

### 5.4. `get_history` — Xem lịch sử bộ nhớ

**Mục đích:** Xem dòng thời gian (timeline) của các thông tin đã lưu gần đây.

**Cách dùng:**

```
Cho tôi xem lịch sử 20 thông tin gần nhất đã lưu vào Memgrap
```

Hữu ích khi bạn muốn:
- Xem lại những gì đã ghi nhớ trong phiên trước
- Kiểm tra xem thông tin đã được lưu chưa
- Hiểu dòng thời gian của dự án

### 5.5. `search_facts` — Tìm kiếm mối quan hệ

**Mục đích:** Tìm các sự kiện (facts) — mối quan hệ giữa các thực thể trong đồ thị.

**Cách dùng:**

```
Tìm tất cả facts liên quan đến quyết định database
```

**Đặc biệt:** Facts trong Memgrap có **tính thời gian** — mỗi fact ghi nhận khi nào nó trở thành đúng (`valid_at`) và khi nào bị thay thế (`invalid_at`). Điều này giúp theo dõi sự thay đổi của quyết định theo thời gian.

Ví dụ:
- Fact 1: "Dự án dùng SQLite" (valid: 01/01 → invalid: 15/02)
- Fact 2: "Dự án dùng PostgreSQL" (valid: 15/02 → hiện tại)

### 5.6. `index_codebase` — Đánh chỉ mục code

**Mục đích:** Quét và đánh chỉ mục một thư mục code vào đồ thị tri thức. Memgrap sẽ phân tích cú pháp (parse) để trích xuất hàm, class, import.

**Chế độ hoạt động:**

| Chế độ | Tham số | Mô tả |
|--------|---------|-------|
| **Incremental** (mặc định) | `full=False` | Chỉ index file **mới** hoặc **đã thay đổi** (so sánh mtime với `indexed_at` trong Neo4j) |
| **Full re-index** | `full=True` | Xóa toàn bộ chỉ mục cũ và index lại từ đầu |

**Tự động index khi bắt đầu phiên:** Mỗi khi bạn mở Claude Code, Memgrap tự động chạy incremental index **ở chế độ nền** — bạn không cần thao tác gì. Chỉ file mới hoặc đã sửa đổi kể từ lần index trước mới được xử lý.

**Cách dùng thủ công:**

```
Đánh chỉ mục thư mục src của dự án hiện tại vào Memgrap
```

```
Index thư mục D:/myproject/src với các file .py và .ts
```

```
Index lại toàn bộ thư mục src (full=True)
```

**Thông tin được trích xuất:**
- **CodeFile** — Tên file, đường dẫn, ngôn ngữ
- **CodeFunction** — Tên hàm, tham số, dòng bắt đầu/kết thúc
- **CodeClass** — Tên class, phương thức
- **CodeImport** — Các thư viện được import

**Ngôn ngữ hỗ trợ (15 ngôn ngữ, 21 extensions):**
- **Mặc định:** Python (`.py`), JavaScript (`.js`, `.jsx`), TypeScript (`.ts`, `.tsx`)
- **Mở rộng:** Go (`.go`), Rust (`.rs`), Java (`.java`), C (`.c`, `.h`), C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx`), C# (`.cs`), Ruby (`.rb`), PHP (`.php`), Kotlin (`.kt`, `.kts`), Swift (`.swift`)

**Lưu ý:** Tính năng này ghi trực tiếp vào Neo4j mà không cần gọi OpenAI, nên **không tốn chi phí API**.

### 5.7. `get_status` — Kiểm tra trạng thái

**Mục đích:** Kiểm tra kết nối và trạng thái hoạt động của Memgrap.

**Cách dùng:**

```
Kiểm tra trạng thái Memgrap
```

Kết quả bao gồm:
- Trạng thái kết nối Neo4j
- Thông tin cấu hình (URI, group_id)
- Trạng thái khởi tạo (initialized hay chưa)

---

## 6. Dashboard

Memgrap đi kèm một giao diện web (dashboard) để bạn trực quan hóa và khám phá đồ thị tri thức.

### Khởi động Dashboard

Dashboard chạy tự động cùng Docker Compose. Nếu chưa chạy:

```bash
cd <thư-mục-memgrap>
docker compose up -d
```

Truy cập: **[http://localhost:3001](http://localhost:3001)**

### Các tab trong Dashboard

Dashboard có **4 tab** chính:

#### Graph — Khám phá đồ thị

- Hiển thị đồ thị tri thức dưới dạng **biểu đồ lực** (force-directed graph) tương tác
- Các **nút (nodes)** đại diện cho thực thể: quyết định, công cụ, khái niệm, v.v.
- Các **cạnh (edges)** đại diện cho mối quan hệ giữa các thực thể
- **Click** vào nút để xem chi tiết
- **Kéo thả** để di chuyển nút
- **Cuộn chuột** để phóng to/thu nhỏ

#### Sessions — Lịch sử phiên làm việc

- Hiển thị danh sách các phiên Claude Code đã được ghi nhận
- Mỗi phiên bao gồm: thời gian, nhánh git, commit gần nhất, file thay đổi
- Click vào phiên để xem chi tiết ngữ cảnh git tại thời điểm đó
- Hữu ích để theo dõi tiến độ làm việc theo thời gian

#### Code — Chỉ mục code

- Hiển thị cây thư mục (file tree) của code đã được đánh chỉ mục
- Xem danh sách hàm, class, import trong từng file
- Giúp Claude Code hiểu cấu trúc dự án nhanh hơn

#### Stats — Thống kê

- Tổng số thực thể (entities) trong đồ thị
- Tổng số mối quan hệ (facts/edges)
- Số phiên làm việc đã ghi nhận
- Số file code đã đánh chỉ mục
- Tổng quan sức khỏe hệ thống

---

## 7. Cấu hình nâng cao

Toàn bộ cấu hình nằm trong file `.env` tại thư mục gốc Memgrap.

### Các tùy chọn cấu hình

```bash
# === Bắt buộc ===
OPENAI_API_KEY=sk-proj-...       # API key của OpenAI

# === Kết nối Neo4j ===
NEO4J_URI=bolt://localhost:7687  # Địa chỉ Neo4j (mặc định)
NEO4J_USER=neo4j                 # Tên đăng nhập (mặc định)
NEO4J_PASSWORD=password           # Mật khẩu (mặc định)

# === Tùy chỉnh (không bắt buộc) ===
LLM_MODEL=gpt-4o-mini            # Model LLM dùng để trích xuất thực thể
LLM_SMALL_MODEL=gpt-4o-mini      # Model nhỏ cho tác vụ phụ
EMBEDDING_MODEL=text-embedding-3-small  # Model tạo vector nhúng
GROUP_ID=default                  # Nhóm dữ liệu (xem giải thích bên dưới)
SEMAPHORE_LIMIT=5                 # Giới hạn số tác vụ đồng thời
```

### GROUP_ID — Phân tách dữ liệu

`GROUP_ID` cho phép bạn tách biệt dữ liệu giữa các dự án hoặc ngữ cảnh khác nhau trên cùng một Neo4j database.

- Mặc định: `default`
- Ví dụ: đặt `GROUP_ID=project-alpha` cho dự án Alpha, `GROUP_ID=project-beta` cho dự án Beta
- Mỗi GROUP_ID tạo một không gian dữ liệu riêng biệt

### Thay đổi model OpenAI

Nếu bạn muốn dùng model mạnh hơn (hoặc rẻ hơn):

```bash
LLM_MODEL=gpt-4o         # Model mạnh hơn, chính xác hơn, tốn hơn
LLM_MODEL=gpt-4o-mini    # Model mặc định, cân bằng giữa chất lượng và chi phí
```

Sau khi thay đổi `.env`, **khởi động lại Claude Code** để áp dụng.

---

## 8. Xử lý sự cố

### Neo4j không chạy

**Triệu chứng:** Claude Code báo lỗi "Failed to connect to Neo4j" hoặc `get_status` trả về lỗi.

**Cách khắc phục:**

```bash
# Kiểm tra Docker đang chạy
docker ps

# Nếu không thấy container memgrap-neo4j, khởi động lại:
cd <thư-mục-memgrap>
docker compose up -d

# Kiểm tra trạng thái container:
docker compose ps

# Xem log nếu vẫn lỗi:
docker compose logs neo4j
```

**Lưu ý:** Neo4j cần khoảng 15-30 giây để sẵn sàng sau khi khởi động. Memgrap sẽ tự động thử lại kết nối 3 lần với thời gian chờ tăng dần (2s, 4s, 6s).

### OpenAI API key thiếu hoặc sai

**Triệu chứng:** Lỗi "OPENAI_API_KEY is not set" hoặc "Invalid API key".

**Cách khắc phục:**

1. Mở file `.env` trong thư mục Memgrap
2. Kiểm tra dòng `OPENAI_API_KEY=...`
3. Đảm bảo key bắt đầu bằng `sk-` và không có khoảng trắng thừa
4. Lưu file và khởi động lại Claude Code

```bash
# Kiểm tra nhanh:
cd <thư-mục-memgrap>
python -c "from src.config import get_settings; s = get_settings(); print('OK' if s.openai_api_key else 'MISSING')"
```

### MCP không kết nối

**Triệu chứng:** Claude Code không nhận diện Memgrap, không có tool `remember`/`recall`.

**Cách khắc phục:**

1. Kiểm tra file `.mcp.json` tồn tại trong thư mục Memgrap:

```bash
# Xem nội dung .mcp.json
cat <thư-mục-memgrap>/.mcp.json
```

Nội dung đúng sẽ có dạng:

```json
{
  "mcpServers": {
    "MEMGRAP": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "<đường-dẫn-tới-thư-mục-memgrap>"
    }
  }
}
```

2. Nếu file không tồn tại hoặc sai, chạy lại script cài đặt (`setup.bat` hoặc `setup.sh`)
3. **Khởi động lại Claude Code** (bắt buộc sau khi thay đổi `.mcp.json`)

### Docker Desktop không chạy

**Triệu chứng:** Lỗi "Cannot connect to the Docker daemon".

**Cách khắc phục:**
- Mở Docker Desktop
- Đợi cho đến khi biểu tượng Docker ở taskbar chuyển sang trạng thái sẵn sàng (không còn loading)
- Thử lại lệnh `docker compose up -d`

### Dashboard không truy cập được

**Triệu chứng:** Không mở được [http://localhost:3001](http://localhost:3001).

**Cách khắc phục:**

```bash
# Kiểm tra container dashboard đang chạy
docker compose ps

# Nếu chưa build dashboard:
docker compose up -d --build dashboard

# Xem log dashboard:
docker compose logs dashboard
```

**Lưu ý:** Dashboard phụ thuộc vào Neo4j — Neo4j phải healthy trước khi dashboard khởi động.

### Dữ liệu không hiển thị trên Dashboard

**Triệu chứng:** Dashboard mở được nhưng không có dữ liệu.

**Nguyên nhân có thể:**
- Chưa lưu thông tin nào qua `remember`
- GROUP_ID trong `.env` khác với GROUP_ID khi lưu dữ liệu

**Cách khắc phục:**
- Thử lưu thông tin test: nói với Claude Code "Hãy nhớ rằng đây là lần test đầu tiên"
- Refresh Dashboard và kiểm tra tab Graph

---

## 9. FAQ

### Memgrap có miễn phí không?

Memgrap là phần mềm mã nguồn mở (MIT license), hoàn toàn miễn phí. Tuy nhiên, bạn cần trả phí cho:
- **OpenAI API** — chi phí trích xuất thực thể và tạo vector nhúng (sử dụng `gpt-4o-mini` nên rất rẻ, khoảng vài cent cho hàng trăm lần gọi)
- **Docker** — miễn phí cho sử dụng cá nhân

### Dữ liệu lưu ở đâu?

Tất cả dữ liệu được lưu trong Neo4j database chạy trên máy local của bạn (qua Docker). Dữ liệu **không** được gửi lên bất kỳ server nào ngoài OpenAI API (để xử lý trích xuất thực thể).

Docker volume `neo4j_data` lưu trữ dữ liệu — ngay cả khi bạn tắt container, dữ liệu vẫn được giữ lại.

### Có thể xóa dữ liệu không?

Có. Bạn có thể:
- Xóa toàn bộ dữ liệu bằng cách xóa Docker volume:
  ```bash
  docker compose down -v
  docker compose up -d
  ```
- Hoặc xóa dữ liệu chọn lọc qua Neo4j Browser tại [http://localhost:7474](http://localhost:7474)

### Memgrap có hoạt động khi không có internet không?

**Không hoàn toàn.** Memgrap cần gọi OpenAI API để:
- Trích xuất thực thể từ văn bản (khi dùng `remember`)
- Tạo vector nhúng cho tìm kiếm ngữ nghĩa (khi dùng `recall`, `search_facts`)

Tuy nhiên, `index_codebase` và `get_status` **không cần** OpenAI API nên vẫn hoạt động offline.

### Tốn bao nhiêu dung lượng ổ cứng?

- Docker image Neo4j: khoảng 500MB
- Docker image Dashboard: khoảng 200MB
- Dữ liệu đồ thị: phụ thuộc vào lượng thông tin lưu, thường dưới 100MB cho dự án vừa

### Có thể dùng cho nhiều dự án cùng lúc không?

Có. Sử dụng `GROUP_ID` trong file `.env` để phân tách dữ liệu giữa các dự án. Xem phần [GROUP_ID](#group_id--phân-tách-dữ-liệu) ở mục Cấu hình nâng cao.

### Session hooks là gì?

Memgrap tự động ghi nhận ngữ cảnh git (nhánh, commit gần nhất, file thay đổi) mỗi khi bạn bắt đầu và kết thúc phiên Claude Code. Tính năng này được cài đặt tự động, bạn không cần cấu hình gì thêm.

### Dùng model OpenAI nào để tiết kiệm nhất?

Mặc định Memgrap dùng `gpt-4o-mini` — đây là model rẻ nhất và đủ tốt cho tác vụ trích xuất thực thể. Chi phí trung bình khoảng $0.01-0.05/ngày cho sử dụng bình thường.

### Có hỗ trợ model khác ngoài OpenAI không?

Hiện tại Memgrap sử dụng OpenAI cho cả LLM và embedding. Graphiti Core (engine bên dưới) có hỗ trợ các provider khác nhưng chưa được cấu hình trong Memgrap.

---

*Phiên bản: 1.0 — Cập nhật lần cuối: Tháng 3/2026*
