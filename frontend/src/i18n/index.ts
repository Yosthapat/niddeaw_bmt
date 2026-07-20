import { createI18n } from 'vue-i18n'
import th from './locales/th'
import en from './locales/en'

export type Locale = 'th' | 'en'

const STORAGE_KEY = 'niddeaw_bmt_locale'

function detectLocale(): Locale {
  return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'th'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'th',
  messages: { th, en },
})

export function setLocale(locale: Locale): void {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

export function currentLocale(): Locale {
  return i18n.global.locale.value as Locale
}

export default i18n
