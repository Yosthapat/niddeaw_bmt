# ตั้งค่า LINE (ผูก LINE กับชื่อสมาชิก)

ทำครั้งเดียว ประมาณ 15 นาที ทำบนคอมจะง่ายที่สุด เมื่อเสร็จแล้ว:

- สมาชิกกดเมนูใน LINE OA ของก๊วน › เข้าสู่ระบบด้วย LINE อัตโนมัติ (ไม่ต้องตั้งรหัส)
- เลือกชื่อตัวเองในก๊วน › แอดมินกด **ยืนยัน** ในหน้า **จัดการสมาชิก** (กล่องสีเขียว "คำขอผูก LINE" ด้านบน)
- ผูกผิดคน › แอดมินกด **แก้ไข** ที่ชื่อนั้น › **ยกเลิกการผูก LINE**

ขั้นต่อไป (เช็คอินด้วย QR, เช็คเอาท์ และดูบิลเอง) จะใช้การผูกนี้

> ทั้ง Channel ID และ LIFF ID ไม่ใช่รหัสลับ แต่ **Channel secret** เป็นรหัสลับ ระบบนี้ไม่ใช้ ห้ามส่งให้ใคร รวมถึงห้ามส่งให้ Claude ด้วย

---

## 1. เปิด Messaging API ให้ LINE OA ของก๊วน

LINE ให้ user id คนละชุดในแต่ละ **provider** ดังนั้นช่องทาง LINE Login ต้องอยู่ provider เดียวกับ OA ของก๊วน

1. เปิด <https://manager.line.biz> › เลือก OA ของก๊วน
2. **ตั้งค่า (Settings)** › **Messaging API** › **ใช้ Messaging API (Enable)**
3. ให้เลือก provider ถ้ายังไม่มี ให้สร้างใหม่ ตั้งชื่อ เช่น `นิดเดียว BMT`

ถ้า OA เปิด Messaging API ไว้แล้ว ให้จดชื่อ provider ที่แสดงอยู่ในหน้านั้น

## 2. สร้างช่องทาง LINE Login

1. เปิด <https://developers.line.biz/console/> แล้ว login ด้วยบัญชี LINE เดียวกับที่เป็นแอดมิน OA
2. กด provider จากข้อ 1 › **Create a new channel** › **LINE Login**
   - Region: **Thailand**
   - Channel name: `นิดเดียว BMT`
   - App types: ติ๊ก **Web app**
   - ใส่อีเมลแล้วกด **Create**
3. แท็บ **Basic settings** › จด **Channel ID** (ตัวเลข 10 หลัก)

## 3. สร้าง LIFF app

1. ในช่องทางเดียวกัน แท็บ **LIFF** › **Add**
   - LIFF app name: `นิดเดียว BMT`
   - Size: **Full**
   - Endpoint URL: `https://niddeaw-bmt.yosthapatk-mbai.workers.dev/line`
   - Scopes: ติ๊ก **openid** และ **profile** (ต้องมี openid ไม่งั้นระบบยืนยันตัวตนไม่ได้)
   - Add friend option (Bot link feature): **On (Normal)** เพื่อชวนเพิ่มเพื่อน OA ไปด้วย
   - กด **Add**
2. จด **LIFF ID** (หน้าตาแบบ `1234567890-AbCdEfGh`) และ **LIFF URL** (`https://liff.line.me/1234567890-AbCdEfGh`)

## 4. เปิดใช้งานช่องทาง (Publish)

ช่องทางใหม่อยู่สถานะ **Developing** ซึ่งให้ login ได้เฉพาะแอดมินในหน้า console เท่านั้น
ด้านบนของหน้าช่องทาง กด **Developing** › **Publish** เพื่อให้สมาชิกทุกคนใช้ได้

## 5. ใส่ค่าใน Render

1. เปิด <https://dashboard.render.com> › service ของ backend › **Environment**
2. เพิ่ม 2 ค่า:
   - `LINE_LOGIN_CHANNEL_ID` = Channel ID จากข้อ 2
   - `LINE_LIFF_ID` = LIFF ID จากข้อ 3
3. **Save changes** แล้วรอ deploy เสร็จ (ประมาณ 2–3 นาที)

ถ้ายังไม่ใส่ หน้า `/line` จะขึ้นว่า "ยังเปิดใช้ LINE ไม่ได้" ส่วนอื่นของเว็บใช้งานได้ปกติ

## 6. ใส่ลิงก์ในเมนูของ OA

1. <https://manager.line.biz> › OA ของก๊วน › **ริชเมนู (Rich menus)** › **สร้าง**
2. เลือกเทมเพลต แล้วให้ปุ่มหนึ่งเป็น **ลิงก์** ไปที่ LIFF URL จากข้อ 3 ตั้งชื่อปุ่ม เช่น `ผูกชื่อ / เช็คอิน`
3. ตั้งช่วงเวลาแสดงผล แล้วกด **บันทึก**

หรือส่ง LIFF URL ในกลุ่ม LINE ของก๊วนก็ได้ กดแล้วเปิดใน LINE ทันที

## 7. ทดลอง

1. เปิด LIFF URL ใน LINE บนมือถือ › ต้องเห็นชื่อ LINE ของตัวเอง และรายชื่อสมาชิกให้เลือก
2. เลือกชื่อ › กด **ใช่ ฉันคือ …**
3. บนคอม เปิดหน้าแอดมิน › **จัดการสมาชิก** › กล่อง "คำขอผูก LINE" › **ยืนยัน**
4. กลับไปที่ LINE แล้วเปิดลิงก์อีกครั้ง › ต้องขึ้นการ์ด **LINKED** พร้อมชื่อในก๊วน

### ถ้าไม่ได้

| อาการ | สาเหตุ |
| --- | --- |
| "ยังเปิดใช้ LINE ไม่ได้" | ยังไม่ได้ใส่ 2 ค่าใน Render หรือยัง deploy ไม่เสร็จ |
| "LINE ยืนยันตัวตนไม่ผ่าน" | `LINE_LOGIN_CHANNEL_ID` ไม่ตรงกับช่องทางที่สร้าง LIFF |
| "LINE gave no ID token" | LIFF ไม่ได้ติ๊ก scope **openid** |
| คนอื่น login ไม่ได้ แต่แอดมินได้ | ช่องทางยังเป็น Developing ให้ Publish (ข้อ 4) |
| เปิดแล้วไปหน้าอื่น | Endpoint URL ต้องลงท้ายด้วย `/line` |
