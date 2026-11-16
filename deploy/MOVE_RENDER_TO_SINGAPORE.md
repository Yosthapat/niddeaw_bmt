# ย้าย backend (Render) จาก Oregon ไป Singapore

## ทำไม

Render รันอยู่ที่ **Oregon (สหรัฐฯ)** แต่ Supabase อยู่ที่ **Singapore** ทุกครั้งที่ backend
ถามฐานข้อมูล ต้องข้ามแปซิฟิกไปกลับ ใช้เวลาราว 0.2 วินาที (Supabase edge log บอกว่า
`origin_time` ประมาณ 200–220 ms) หน้าหนึ่งถามหลายครั้ง เลยช้าทั้งเว็บ ถ้าย้ายไป
Singapore จะเหลือไม่กี่มิลลิวินาทีต่อครั้ง และใกล้ผู้ใช้ในไทยด้วย

Render **เปลี่ยน region ของ service เดิมไม่ได้** ต้องสร้าง service ใหม่ใน Singapore
แล้วชี้หน้าเว็บไปที่ตัวใหม่ ถ้าทำตามลำดับด้านล่าง เว็บจะไม่ดับระหว่างย้าย

**สิ่งที่ไม่ต้องแก้:** Supabase, LINE Developers (LIFF ชี้ไปที่หน้าเว็บ niddeaw.fyi ไม่ได้ชี้
ไปที่ API), ข้อมูลในฐานข้อมูล และไฟล์รูป

## ก่อนเริ่ม

- **เลือกช่วงที่ไม่มีก๊วนเปิด และไม่ใช่วันแข่งทัวร์นาเมนต์** ใช้เวลาราว 30–45 นาที
- **ช่วงที่ service เก่ากับใหม่รันพร้อมกัน (2–3 วัน):**
  - แคชทัวร์นาเมนต์ของแต่ละตัวแยกกัน คนที่ยังใช้แอปเวอร์ชันเก่าอาจเห็นข้อมูลช้ากว่าคนอื่นได้ไม่เกิน 30 วินาที
  - แพ็กฟรีให้ชั่วโมงรันรวม 750 ชั่วโมงต่อเดือนต่อบัญชี สองตัวรันพร้อมกันใช้ชั่วโมงเร็วขึ้นเท่าตัว อย่าเปิดคู่กันนานเกิน 2–3 วัน

## ขั้นตอน

### 1. จด Environment ของ service เดิม

Render → service เดิม (`niddeaw-bmt`) → **Environment** แล้วคัดลอกค่าทุกตัวเก็บไว้
**อย่าส่งค่าพวกนี้ในแชตหรือที่สาธารณะ** โดยเฉพาะ key กับ secret

| Key | หมายเหตุ |
|---|---|
| `SUPABASE_URL` | |
| `SUPABASE_SERVICE_ROLE_KEY` | ความลับ |
| `JWT_SECRET` | ความลับ · **ต้องใช้ค่าเดิมเป๊ะ** ไม่อย่างนั้นทุกคนจะหลุด login ทั้งแอดมินและ LINE |
| `JWT_EXPIRE_MINUTES` | ถ้ามี |
| `CORS_ORIGINS` | `https://niddeaw.fyi,https://niddeaw-bmt.yosthapatk-mbai.workers.dev` |
| `ENV` | `production` |
| `PYTHON_VERSION` | `3.13.11` |
| `LINE_LOGIN_CHANNEL_ID` | |
| `LINE_LIFF_ID` | |
| `LINE_TOKEN_MINUTES` | ถ้ามี |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ความลับ · ถ้าใช้ sync Google Sheets |
| `SHEETS_SPREADSHEET_ID` | ถ้ามี |
| `SHEETS_SYNC_SECRET` | ความลับ · ถ้ามี |

ถ้าใน service เดิมมี key อื่นนอกจากนี้ ให้คัดลอกมาด้วยทั้งหมด

### 2. สร้าง service ใหม่ใน Singapore

Render → **New → Web Service** → เลือก repo `Yosthapat/niddeaw_bmt`

| ช่อง | ค่า |
|---|---|
| Name | `niddeaw-bmt-sg` (URL จะเป็น `https://niddeaw-bmt-sg.onrender.com`) |
| **Region** | **Singapore (Southeast Asia)** |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install pdm && pdm export -o requirements.txt --prod --without-hashes && pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path (ใน Advanced) | `/health` |
| Auto-Deploy | Yes |

แล้วใส่ Environment ทุกตัวจากข้อ 1 → **Create Web Service** → รอ build เสร็จ (ราว 3–5 นาที)

### 3. ทดสอบตัวใหม่ (ยังไม่มีใครใช้)

เปิดในเบราว์เซอร์:

- `https://niddeaw-bmt-sg.onrender.com/health` → ต้องขึ้น ok
- `https://niddeaw-bmt-sg.onrender.com/api/tournament` → ต้องเห็นข้อมูลงาน

ส่ง URL ใหม่มาให้ Claude วัดเวลาเทียบกับตัวเดิม และยิงทดสอบโหลดได้

### 4. ชี้หน้าเว็บไปที่ตัวใหม่

**4.1 โค้ด:** ให้ Claude ทำ PR เปลี่ยน URL ทุกที่ที่อ้างถึง API ตัวเดิม

- `frontend/.env.production` (`VITE_API_BASE_URL`)
- `.github/workflows/keep-alive.yml` (ping กันหลับ)
- `.github/workflows/sheets-sync.yml` (sync Google Sheets รายสัปดาห์)
- `deploy/render.yaml` (`name` และ `region: singapore`) และเอกสารใน `deploy/`

**4.2 Cloudflare:** Workers & Pages → `niddeaw-bmt` → **Settings → Variables and Secrets**
(ส่วน Build) ถ้ามี `VITE_API_BASE_URL` ให้แก้เป็น URL ใหม่ด้วย เพราะค่าที่ตั้งใน Cloudflare
จะทับค่าในไฟล์ `.env.production`

**4.3** merge PR → Cloudflare build หน้าเว็บใหม่เอง (ราว 1–2 นาที) ถ้าแก้ค่าใน Cloudflare
หลัง merge ให้กด **Retry deployment** เพื่อ build ใหม่

### 5. เช็คหลังย้าย

- รีเฟรชเว็บ (Ctrl + Shift + R) แล้วลอง:
  - login แอดมิน
  - เปิดหน้าก๊วนคืนนี้
  - หน้า `/tournament`
  - เปิดใน LINE (หน้า LINE OA)
- ทุกคนยัง login อยู่เหมือนเดิม เพราะใช้ `JWT_SECRET` ค่าเดิม
- ใน Supabase → Logs ฝั่ง edge จะเห็นคำขอมาจาก Singapore แทน Oregon

### 6. ping กันหลับ

- **GitHub Actions** (`keep-alive.yml`) เปลี่ยนในข้อ 4.1 แล้ว
- **cron-job.org** ถ้ามีงาน ping `/health` ของตัวเดิม ให้เปลี่ยนเป็นตัวใหม่

### 7. ปิดตัวเดิม (หลังผ่านไป 2–3 วัน)

แอปที่ติดตั้งบนมือถือ (PWA) อาจยังใช้เวอร์ชันเก่าที่ชี้ไปตัวเดิมอยู่ 1–2 วัน จนกว่าจะอัปเดต
เลยยังไม่ควรปิดตัวเดิมทันที

พอผ่านไป 2–3 วัน: Render → service เดิม → **Settings → Suspend Web Service**
ใช้งานได้ปกติสักพัก ค่อย **Delete Web Service**

## ทางเลือก: ตั้งโดเมนของ API เอง (แนะนำ)

ใช้ `https://api.niddeaw.fyi` แทน `*.onrender.com` ครั้งหน้าจะย้ายหรือเปลี่ยน service
ก็ไม่ต้องแก้ URL ในโค้ดอีก

1. Render → service ใหม่ → **Settings → Custom Domains → Add** → `api.niddeaw.fyi`
2. Cloudflare → DNS ของ `niddeaw.fyi` → เพิ่ม **CNAME** `api` → `niddeaw-bmt-sg.onrender.com`
   ตั้งเป็น **DNS only (เมฆสีเทา)** ก่อน จนกว่า Render จะออกใบรับรอง SSL ให้
3. รอ Render ขึ้น Verified
4. ใช้ `https://api.niddeaw.fyi` เป็น URL ในข้อ 4 แทน
