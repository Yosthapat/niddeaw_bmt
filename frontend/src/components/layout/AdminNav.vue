<script setup lang="ts">
/**
 * The top of every admin screen: the home hero's world in a shorter strip
 * — violet sky, stars, the striped sun, the running grid floor — with the
 * screen's name, a line about it, and its mascot (PageBanner.vue, compact).
 *
 * The admin's navigation used to live here as a strip of twelve buttons.
 * It moved to where the public site keeps its own: the glass bar at the
 * top on a desktop (AppHeader.vue) and a bar at the bottom of a phone,
 * where a thumb reaches it (AdminTabBar.vue). Every admin view still
 * renders <AdminNav /> first, so the banner reaches all of them.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import PageBanner from '@/components/common/PageBanner.vue'
import { adminPage } from './adminPages'

const route = useRoute()
const { t } = useI18n()
const page = computed(() => adminPage(route.path))
</script>

<template>
  <PageBanner
    v-if="page"
    compact
    decorative-title
    :eyebrow="page.eyebrow"
    :title="t(`admin.nav.${page.nav}`)"
    :sub="t(`admin.banner.${page.banner}`)"
    :mascot="page.mascot"
  />
</template>
