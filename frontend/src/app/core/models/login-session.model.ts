// Note: login request uses form data and session request is a blank JSON object, 
// hence no interfaces
export interface LoginResponse {
    access_token: string;
    token_type: string;
    expires_at: string;
    is_admin: boolean;
}

export interface SessionResponse {
    session_id: string;
    name: string;
    token: LoginResponse;
}