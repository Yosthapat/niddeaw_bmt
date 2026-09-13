/** Mirrors backend app/models/season.py. A season is one calendar year;
 * see backend/app/services/season_service.py for why it's derived from
 * session dates rather than stored. */
export interface Season {
  number: number
  year: number
  start_date: string
  end_date: string
  is_current: boolean
}
