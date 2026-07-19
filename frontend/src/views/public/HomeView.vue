<script setup lang="ts">
// Static club intro + contact — there's no backend-driven "club info" table
// (out of scope per the issue doc), so this content is edited directly here.
</script>

<template>
  <main class="mx-auto max-w-3xl px-4 py-10 text-center">
    <img
      src="/pwa-icons/pwa-512x512.png"
      alt="นิดเดียว Badminton Club logo"
      class="mx-auto h-32 w-32 rounded-full ring-4 ring-brand-pink"
    />
    <h1 class="mt-6 text-3xl font-extrabold text-brand-pink">นิดเดียว Badminton Club</h1>
    <p class="mt-3 text-white/70">
      ก๊วนแบดมินตันสายมันส์ ธีม Milk → Soju → Beer → Highball → Vodka —
      เช็คอิน จัดคู่ตาม ELO และคิดเงินอัตโนมัติ
    </p>

    <div class="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <RouterLink
        to="/members"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-4 text-sm font-semibold text-white hover:bg-brand-pink-dark/20"
      >
        สมาชิก
      </RouterLink>
      <RouterLink
        to="/ranking"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-4 text-sm font-semibold text-white hover:bg-brand-pink-dark/20"
      >
        อันดับ
      </RouterLink>
      <RouterLink
        to="/hall-of-fame"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-4 text-sm font-semibold text-white hover:bg-brand-pink-dark/20"
      >
        Hall of Fame
      </RouterLink>
      <RouterLink
        to="/matches"
        class="rounded-xl border border-brand-pink-dark/40 bg-white/5 px-3 py-4 text-sm font-semibold text-white hover:bg-brand-pink-dark/20"
      >
        ผลแมตช์
      </RouterLink>
    </div>

    <section class="mt-10 rounded-xl border border-brand-pink-dark/40 bg-white/5 p-6 text-left">
      <h2 class="text-lg font-bold text-brand-pink">ติดต่อผู้จัดก๊วน</h2>
      <p class="mt-2 text-sm text-white/70">
        สอบถามตารางตี / สมัครสมาชิกใหม่ ทักแอดมินได้ทาง LINE หรือโทรศัพท์
        (ข้อมูลติดต่อ — แก้ไขได้ที่
        <code class="rounded bg-black/40 px-1">src/views/public/HomeView.vue</code>)
      </p>
    </section>
  </main>
</template>
