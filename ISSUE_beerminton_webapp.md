# 🏸 นิดเดียว Badminton Club — Web App (Clone BMBAD + Admin Billing/Matching)

## Overview

สร้างเว็บแอปจัดการก๊วนแบดมินตัน "นิดเดียว Badminton Club" โดย **clone ฟีเจอร์หลักทั้งหมดจาก bmbad.com (BaanMoon R19)** แล้วเพิ่มหน้า Admin สำหรับ **คิดเงิน (Billing)** และ **จัดคู่ผู้เล่น (Matchmaking)** พร้อม theme **Black-Pink** ตาม logo ก๊วน (แนบไฟล์: `logo-nidedeaw-badminton-club.jpg` ที่ root ของ repo — แมวมงกุฎถือไม้แบด สี pink #ec4899 บนพื้นดำ)

## ✅ Decisions Resolved (2026-07-19 review)

| ประเด็น | เดิม | ตัดสินใจแล้ว |
|---|---|---|
| Player login | TBD (LINE login / simple auth) | **ไม่มี player login ใน Phase 1** — public site เป็น read-only ทั้งหมด (Home/Member List/Ranking/Hall of Fame/Match history) ส่วนเช็คอิน-เอาท์และบันทึกผลแมตช์ทำผ่าน **Admin panel เท่านั้น** (admin กดเช็คอินแทนผู้เล่นหน้าคอร์ท) |
| Data access path | ไม่ระบุ | **Frontend ต้องคุยผ่าน FastAPI เท่านั้น** ห้าม frontend ต่อ Supabase ตรงด้วย anon key เด็ดขาด — Supabase (service-role key) ใช้ฝั่ง backend เท่านั้น เพื่อกัน `billings`/`admins` รั่ว |
| Real-time updates | "real-time เหมือนกัน" คลุมเครือ | ใช้ **polling ผ่าน FastAPI** (เช่น refetch ทุก 5-10 วิบนหน้า check-in/matching) แทน WebSocket/Supabase Realtime — พอสำหรับก๊วน 30-50 คน ลดความซับซ้อน |
| Match score format | ไม่ระบุ | บันทึกเป็น **sets/games** (เช่น `[[21,15],[18,21],[21,19]]`) ไม่ใช่ single number เพื่อคำนวณ win/draw/loss ให้ตรง |
| Deploy | ต้อง deploy จริงตาม Acceptance Criteria | **Phase นี้ทำแค่ scaffold code + deploy config** (render.yaml, wrangler config, .env.example, migration SQL) ยังไม่ deploy จริงเพราะยังไม่มี Supabase/Render/Cloudflare account — deploy จริงทำหลังคุณสร้าง account/ส่ง credentials |

---

## 🎯 Tech Stack (ตัดสินใจแล้ว)

| Layer | เลือกใช้ | เหตุผล |
|---|---|---|
| Frontend | **Vue 3 + TypeScript + Vite + TailwindCSS + PWA** | ตาม stack เดิมที่ใช้ประจำ |
| Backend | **FastAPI + Python (PDM)** | ตาม stack เดิม, type-safe ด้วย mypy |
| Database | **Supabase (PostgreSQL)** | ดูหัวข้อ "Database Decision" ด้านล่าง |
| Storage รูปผู้เล่น | **Supabase Storage** (bucket `avatars`) | ผูกกับ DB เดียวกัน ไม่ต้องเปิด service เพิ่ม |
| Frontend Deploy | **Cloudflare Pages** | ดูหัวข้อ "Deploy Decision" ด้านล่าง |
| Backend Deploy | **Render (free tier)** | รองรับ FastAPI แบบ persistent process ได้ฟรี |
| Anti cold-start | **cron-job.org** ping `/health` ทุก 10 นาที | Render free tier sleep หลัง 15 นาทีไม่มี traffic |

### Deploy Decision: Cloudflare Pages vs Netlify → **เลือก Cloudflare Pages**

| | Cloudflare Pages | Netlify |
|---|---|---|
| Bandwidth ฟรี | ไม่จำกัด | 100GB/เดือน |
| Build minutes ฟรี | 500 นาที/เดือน | 300 นาที/เดือน |
| Storage รูปในตัว | มี R2 (ถ้าอยากแยกจาก Supabase) | ไม่มี ต้องพึ่ง 3rd party |
| Custom domain + SSL | ฟรี ไม่จำกัด | ฟรี ไม่จำกัด |
| Edge network ในไทย | เร็วมาก (Cloudflare PoP กรุงเทพมี) | ดีอยู่แล้วแต่ Cloudflare เร็วกว่าเล็กน้อย |

Netlify ก็ใช้ได้และง่ายไม่แพ้กัน แต่เลือก Cloudflare Pages เพราะ bandwidth ไม่จำกัด (กันเผื่อกรณีรูปผู้เล่นเยอะ + สมาชิกโหลดพร้อมกันวันแข่ง) และ ecosystem เดียวกับ R2 ถ้าต้องขยาย storage ในอนาคต

### Database Decision: **ต้องมี** — เลือก Supabase (Postgres)

ต้องมี database เพราะ:
1. ข้อมูลต้อง **persist ถาวร** (ประวัติแมตช์, ELO, ยอดเก็บเงิน) — เก็บใน localStorage/ไฟล์อย่างเดียวไม่พอ ข้อมูลหายเวลาเปลี่ยนเครื่อง/ล้าง cache
2. ต้องรองรับ **รูปผู้เล่น (avatar)** — ต้องมีที่เก็บไฟล์แบบถาวรและ query ได้
3. หลายคนต้องเห็นข้อมูล **real-time เหมือนกัน** (ranking, session เช็คอิน) — ไม่ใช่ static site ล้วนๆ
4. Admin ต้องแก้ไข/ลบ/ปรับข้อมูลย้อนหลังได้ (คิดเงิน, จัดคู่)

Supabase ให้ Postgres + Storage + Auth ในตัวเดียว ฟรี 500MB DB / 1GB Storage ซึ่งเพียงพอสำหรับก๊วนขนาด 30-50 คน (รูป avatar บีบขนาด ~100-200KB/รูปก่อนอัพโหลด)

---

## 📋 Feature Scope

### A. Clone จาก BMBAD (ฟีเจอร์เดิมที่ต้องมี)
อ้างอิงจากการสำรวจ bmbad.com:
- [ ] **Home** — หน้าแรกก๊วน แสดงข้อมูลติดต่อผู้จัดก๊วน/แอดมิน
- [ ] **Member List** — ตาราง Game/Win/Draw/Loss/Pts/Avg/Sc(%) ต่อสมาชิก
- [ ] **Today Check-in** — เช็คอินรายวัน แสดงจำนวนคนเช็คอินวันนั้น
- [ ] **Match** — บันทึกผลแมตช์ (Singles/Doubles + รองรับ draw)
- [ ] **Ranking** — จัดอันดับ (รายปี/all-time)
- [ ] **Hall of Fame**
- [ ] **Staff/Admin Login**

### B. ฟีเจอร์เสริมจาก plan เดิม (Beerminton) ที่ยังใช้ต่อ
- [ ] ELO Rating System (5 levels ธีมเครื่องดื่ม: Milk → Soju → Beer → Highball → Vodka)
- [ ] Balanced Matchmaking (จับคู่ตามระดับ / mixed level)
- [ ] Session Management (ลงชื่อ/เช็คอิน-เอาท์)
- [ ] PWA (ติดตั้งบนมือถือได้)

### C. 🆕 ใหม่ในรอบนี้ — Admin Panel

**C1. Billing / คิดเงิน**
- [ ] Admin ตั้งค่า **อัตราค่าหัวต่อชั่วโมง** ต่อ session
- [ ] ระบบคำนวณค่าใช้จ่ายอัตโนมัติจากเวลาเช็คอิน-เอาท์จริงของแต่ละคน
- [ ] Admin ปรับยอดรายบุคคลได้ด้วยมือ (กรณีพิเศษ เช่น มาสาย/จ่ายแทนเพื่อน)
- [ ] สร้าง **PromptPay QR** ต่อคน/ต่อ session
- [ ] มาร์คสถานะจ่ายแล้ว/ค้างจ่าย ต่อคนต่อ session
- [ ] สรุปยอดรายเดือน/รายรอบ ดูย้อนหลังได้

**C2. Matchmaking Management**
- [ ] Admin เลือกผู้เล่นที่เช็คอินแล้วมาจัดคู่ (Auto-suggest ตาม ELO + Manual override)
- [ ] แสดงคิว/รอบถัดไป พร้อมเวลาโดยประมาณ
- [ ] บันทึกผลแมตช์จากหน้า Admin ได้ทันที (อัพเดท ELO อัตโนมัติ)
- [ ] ประวัติการจับคู่ ป้องกันคนกลุ่มเดิมชนกันซ้ำถี่เกินไป (fairness rule พื้นฐาน)

### D. Design
- [ ] Theme: **Black (#0a0a0a) + Pink (#ec4899 / hot pink)** ตาม logo
- [ ] ใช้ logo แมวมงกุฎ (`logo-nidedeaw-badminton-club.jpg`) เป็น favicon + header brand
- [ ] Mobile-first (สมาชิกส่วนใหญ่เข้าจากมือถือหน้าคอร์ท)
- [ ] Dark UI สไตล์ gaming/esports ให้เข้ากับธีม cat-badminton mascot

---

## 🗄️ Data Model (ร่างเบื้องต้น — ให้ Claude Code ปรับตอน implement)

```
players
  id, name, nickname, avatar_url, elo_level, elo_score, phone, line_id, created_at
  (line_id/phone เก็บไว้เป็นข้อมูลติดต่อเฉยๆ — ไม่ใช้ login เพราะ Phase 1 ไม่มี player login)

sessions
  id, date, location, rate_per_hour, status (open/closed), created_by (admin_id)

checkins
  id, session_id, player_id, checkin_time, checkout_time (null = ยังอยู่ในสนาม)
  unique (session_id, player_id)

matches
  id, session_id, type (single/double), team1_player_ids[], team2_player_ids[],
  sets jsonb  -- e.g. [[21,15],[18,21],[21,19]]
  winner (team1/team2/draw), status (in_progress/completed), created_at

billings
  id, session_id, player_id, hours_played, amount_calc, amount_adjusted,
  paid_status (unpaid/paid), promptpay_ref, updated_at
  unique (session_id, player_id)

admins
  id, username, password_hash (bcrypt/argon2), role, created_at
```

---

## ✅ Acceptance Criteria (Phase 1)

- [ ] Public site แสดง Home, Member List, Ranking, Hall of Fame, Match history (read-only, ไม่ต้อง login)
- [ ] Admin เช็คอิน/เอาท์ผู้เล่นแทนหน้า Admin panel (ไม่มี player login ใน Phase 1)
- [ ] Admin login (JWT, password hash ด้วย bcrypt/argon2) แยกจาก public
- [ ] Admin → Billing: คำนวณค่าหัวอัตโนมัติจากเวลาเช็คอิน + gen PromptPay QR ได้
- [ ] Admin → Matching: จัดคู่ผู้เล่นที่เช็คอินอยู่ และบันทึกผลแมตช์ได้
- [ ] อัพโหลด/แสดงรูปโปรไฟล์ผู้เล่นได้ (เก็บใน Supabase Storage)
- [ ] Responsive ใช้งานได้ดีบนมือถือ, ธีม black-pink ตาม logo
- [ ] Deploy ขึ้น Cloudflare Pages (frontend) + Render (backend) + Supabase (DB/Storage) ได้จริง

## ⛔ Out of Scope (Phase ถัดไป)
- Push notification, Achievement badges, Weekly challenge, Season recap (ตามที่เคย scope ไว้ใน plan เดิม — เก็บไว้ทำต่อรอบหน้า)

---

## 📎 Assets
- Logo: `beerminton-assets/logo-nidedeaw-badminton-club.jpg`
