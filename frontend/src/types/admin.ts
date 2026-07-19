export interface Admin {
  id: string
  username: string
  role: string
  created_at: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in_minutes: number
}
