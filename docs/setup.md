# Setup: phần anh phải tự làm

Khoảng 2 giờ, làm một lần. Mỗi mục kết thúc bằng một lệnh; lệnh đó tự kiểm tra và đưa thẳng
token vào GitHub Secrets của repo. Token không hiện ra màn hình và không nằm trong repo hay chat.

> ⚠️ Tên secret có dấu gạch dưới (ví dụ `FB_PAGE_TOKEN`). Nếu phải gõ tay ở đâu đó, hãy copy từ
> file này trong VS Code, không copy từ khung chat.

## 0. Chuẩn bị (5 phút)

1. Mở terminal WSL, vào repo: `cd ~/projects/lab-to-prod`.
2. Kiểm tra GitHub CLI đang đăng nhập đúng tài khoản cá nhân:

   ```bash
   gh auth status
   ```

   Dòng "Active account: true" phải nằm dưới `pqnghiep1354`. Nếu không:

   ```bash
   gh auth switch --user pqnghiep1354
   ```

3. Các script mở trình duyệt để anh đăng nhập. Nếu trình duyệt không tự mở từ WSL, copy đường
   link script in ra và dán vào trình duyệt trên Windows.

Thứ tự gợi ý: Telegram → DEV → Blog → Facebook → YouTube → LinkedIn (dễ trước, khó sau).

## 1. Telegram (10 phút)

1. Trong Telegram: **New Channel** → tên `Nghiep Pham · Lab to Prod` → **Public** → link
   `labtoprod_nghiep` (nếu đã có người dùng thì chọn tên khác và nhớ tên đó).
2. Nhắn `@BotFather` → `/newbot` → đặt tên và username cho bot → BotFather trả về bot token.
3. Vào kênh → **Administrators** → **Add Admin** → tìm bot vừa tạo → bật **Post Messages**.
4. Ảnh đại diện kênh: `brand/option-a/avatar-telegram.png` (hoặc option-b).
5. Chạy:

   ```bash
   python3 scripts/tokens/simple_secrets.py telegram
   ```

   Dán bot token (không hiện khi gõ), rồi nhập username kênh. Script kiểm bot có phải admin
   được đăng bài không, rồi lưu `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHANNEL`.

## 2. DEV (5 phút)

1. Tạo tài khoản tại dev.to (đăng nhập bằng GitHub là nhanh nhất).
2. **Settings → Extensions → DEV Community API Keys** → nhập mô tả `lab-to-prod` → **Generate API Key**.
3. Chạy:

   ```bash
   python3 scripts/tokens/simple_secrets.py devto
   ```

Hashnode: không cần key. API của Hashnode đã tính phí từ 13/05/2026 nên repo chỉ sinh file
`hashnode-<slug>.md` để anh dán tay (tuỳ chọn). Nếu không dùng Hashnode, đặt `hashnode: off`
trong `publish/config.yaml`.

## 3. Blog trên GitHub Pages (5 phút)

1. Repo → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Sau khi merge các PR dựng repo, workflow `blog` tự build. Blog ở
   `https://nghiep-pham-ecosys.github.io/lab-to-prod/`.
3. GoatCounter: tạo tài khoản tại goatcounter.com, chọn một mã (ví dụ `labtoprod`), điền mã đó
   vào `goatcounter` trong `blog/src/site.ts`.
4. Google Search Console: thêm property kiểu **URL prefix** với địa chỉ blog → chọn cách xác
   minh **HTML tag** → copy giá trị `content` vào `searchConsole` trong `blog/src/site.ts` →
   merge → bấm **Verify** → **Sitemaps** → nộp `sitemap-index.xml`.
5. Điền link LinkedIn của anh vào `linkedin` trong `blog/src/site.ts`.

## 4. Facebook Page (25 phút)

1. Page "Lab to Prod" **đã tạo ngày 13/11/2026** (hạng mục Science, technology and engineering, website là
   blog). Còn lại: tải ảnh đại diện `brand/option-d/avatar.png` (800×800, hình tròn) và ảnh bìa
   `brand/option-d/banner-facebook.png` (1640×624, chữ nằm ở vùng giữa nên điện thoại cắt hai bên
   vẫn đọc được). Hai file sinh lại bằng `uv run --with pillow --with pyyaml python brand/build.py d`.
2. developers.facebook.com → **My Apps → Create App** → tên `lab-to-prod`, email liên hệ → use case
   **Manage everything on your Page** → business: chưa gắn → **Create app**. (App `lab-to-prod` đã tạo
   ngày 13/11/2026.)
3. **Use cases → Manage everything on your Page → Customize → Permissions and features**: bấm **Add**
   cho `pages_manage_posts`, `pages_read_engagement` và `read_insights` (`pages_show_list` có sẵn). Thiếu
   bước này thì hộp đăng nhập báo "Invalid Scopes".
4. **App settings → Basic**: App ID ở đầu trang; bấm **Show** để lấy **App Secret** (chỉ dán vào script,
   không gửi qua chat).
5. Giữ app ở chế độ **Development**: anh là admin của app nên vẫn đăng được lên Page của mình. Ở chế độ
   này Facebook tự cho phép redirect về `http://localhost`, không cần khai trong Facebook Login settings
   và không cần thêm App Domain.
6. Chạy:

   ```bash
   python3 scripts/tokens/facebook_token.py
   ```

   Nhập App ID và App Secret. Trình duyệt mở ra: chọn đúng Page, đồng ý các quyền. Script đổi
   sang token dài hạn rồi lưu `FB_PAGE_ID` và `FB_PAGE_TOKEN`.

Kênh `facebook` trong `publish/config.yaml` chính là Page này. Nó chỉ chạy thử (dry run) cho tới khi
biến repository `PUBLISH_LIVE` là `true`. Mỗi bài đăng thành công được ghi vào `published.json` dưới
khoá `facebook`. Bài chia sẻ lại về trang cá nhân là đăng tay: không cần ghi.

Lưu ý: Page token dài hạn không có ngày hết hạn, nhưng quyền truy cập dữ liệu của app hết sau
khoảng 90 ngày không dùng. Workflow `metrics` sẽ báo trước 7 ngày; khi đó chạy lại lệnh trên.

## 5. YouTube (25 phút)

1. Tạo kênh YouTube (hoặc dùng kênh sẵn có), handle gợi ý `@nghiep-labtoprod`. Xác minh số
   điện thoại tại youtube.com/verify. Ảnh kênh `brand/option-a/avatar.png`, banner
   `brand/option-a/banner-youtube.png`.
2. console.cloud.google.com → tạo project `lab-to-prod`.
3. **APIs & Services → Library** → bật **YouTube Data API v3** và **YouTube Analytics API**.
4. **OAuth consent screen**: User type **External** → điền tên app và email → thêm 3 scope:
   `youtube.upload`, `youtube.force-ssl`, `yt-analytics.readonly` → **Publish app** để trạng thái
   là **In production**. (Để ở Testing thì token chết sau 7 ngày.)
5. **Credentials → Create credentials → OAuth client ID** → loại **Desktop app** → ghi lại
   Client ID và Client Secret.
6. Chạy:

   ```bash
   python3 scripts/tokens/youtube_token.py
   ```

   Google sẽ cảnh báo "Google hasn't verified this app": bấm **Advanced → Go to lab-to-prod**.
   Đây là app của chính anh. Script lưu `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

Sau lần upload thật đầu tiên, xem Short có tự công khai đúng giờ không. Tài liệu YouTube (bản
sửa 02/11/2026) nói app chưa kiểm duyệt không còn bị khoá ở chế độ riêng tư; nếu video vẫn
riêng tư sau giờ hẹn thì bật **Public** trong YouTube Studio.

## 6. LinkedIn (20 phút)

1. linkedin.com/developers/apps → **Create app**. LinkedIn bắt gắn app với một LinkedIn Page:
   dùng Page của anh, hoặc tạo một Page trống chỉ để làm chủ app.
2. Tab **Products**: bấm **Request access** cho **Share on LinkedIn** và
   **Sign In with LinkedIn using OpenID Connect**. Hai sản phẩm này được duyệt ngay.
3. Tab **Auth**: mục **Authorized redirect URLs** thêm `http://localhost:8765/callback`. Ghi
   lại **Client ID** và **Client Secret**.
4. Chạy:

   ```bash
   python3 scripts/tokens/linkedin_token.py
   ```

   Script lưu `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` và biến `LINKEDIN_TOKEN_ISSUED`.

Token LinkedIn sống 60 ngày và không gia hạn tự động được. Workflow `metrics` báo trước 7 ngày
(khoảng 10/01/2027 nếu lấy token ngày 14/11); khi đó chạy lại đúng lệnh trên.

## 7. Kiểm tra (5 phút)

```bash
gh secret list --repo nghiep-pham-ecosys/lab-to-prod
```

Phải có 10 secret:

| Kênh | Secret |
| --- | --- |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` |
| Facebook | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| YouTube | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL` |
| DEV | `DEVTO_API_KEY` |

Kiểm tra sức khoẻ token (không đăng gì): **Actions → metrics → Run workflow**. Bước "Token
health" in số ngày còn lại của từng token.

## 8. Cho phép đăng thật

Mặc định mọi thứ là dry-run. Cách bật từng kênh một nằm ở `docs/operations.md`, mục
"Going live, one channel at a time". Tóm tắt: đặt biến repo `PUBLISH_LIVE` thành `true` chỉ khi
anh đã đọc một lần dry-run và thấy đúng.

## 9. Việc tay hằng tuần

| Khi nào | Việc | Thời gian |
| --- | --- | --- |
| Thứ Bảy / Chủ nhật | Đọc PR "Week NN", sửa hoặc comment, merge trước 22:00 Chủ nhật | 15-20 phút |
| Chủ nhật | Mở `content/<tuần>/x-schedule.md`, hẹn giờ 5 post trên x.com | 5 phút |
| Chủ nhật | Xuất số liệu LinkedIn thành `metrics/inbox/linkedin-<tuần>.csv` (mẫu trong `metrics/inbox/README.md`) | 5 phút |
| Thứ Bảy (tuỳ chọn) | Dán `hashnode-<slug>.md` vào Hashnode, điền original URL | 3 phút |
| Mỗi sáng đăng bài | Nếu LinkedIn từ chối bình luận đầu tiên, tự dán link blog vào bình luận | 1 phút |

## 10. Hồ sơ LinkedIn (10 phút)

- **Headline:** `AI Engineer · LLMOps & Agentic AI · Climate AI · From lab scientist to production AI`
- **Banner:** `brand/option-a/banner-linkedin.png`
- **Featured:** thêm link blog `https://nghiep-pham-ecosys.github.io/lab-to-prod/`
- **About (gợi ý, anh sửa cho đúng mình):**

  > I started in a chemistry and materials lab and now build AI systems. I work on LLM
  > evaluation, agents and LLMOps, and I care about climate AI. I write one short technical note
  > every weekday and one long article every Saturday at Lab to Prod, and the publishing
  > pipeline behind it is open source.
