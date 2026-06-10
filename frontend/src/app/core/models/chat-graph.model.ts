// Types are generated from the backend OpenAPI spec via HeyAPI (npm run generate:api).
import type { Message as ApiMessage } from '../api';

export type {
  ChatRequest,
  ChatResponse,
  StudentResponse,
  SummaryFeedbackResponse,
} from '../api';

export type role = ApiMessage['role'];

// Chat message extended with frontend-only display fields (the backend
// Message schema only carries role and content).
export interface Message extends ApiMessage {
  student_name?: string;
  audio_base64?: string;
  audio_id?: string;
}

// The async inline-feedback polling endpoint (/api/v1/chatbot/feedback/{id})
// has no response model in the OpenAPI spec, so these types are kept locally.
export type FeedbackStatus = 'pending' | 'ready' | 'failed';

export interface FeedbackResponse {
  status: FeedbackStatus;
  feedback: string[];
}
