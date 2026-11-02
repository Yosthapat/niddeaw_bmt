/** Mirrors backend app/models/activity_log.py AdminActivityLogEntry. */
export interface AdminActivityLogEntry {
  id: string
  admin_id: string
  admin_username: string
  action: string
  method: string
  path: string
  detail: Record<string, unknown> | null
  created_at: string
}
