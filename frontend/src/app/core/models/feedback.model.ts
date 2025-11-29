/**
 * Feedback type enum matching backend FeedbackType
 */
export type FeedbackType = 'inline' | 'summary';

/**
 * Feedback model representing a feedback configuration
 */
export interface Feedback {
  id: number;
  feedback_type: FeedbackType;
  objective: string;
  instructions: string;
  constraints: string;
  context: string;
  output_format: string;
  created_at: string;
  owner_id?: number | null;
  is_global?: boolean;
}

/**
 * Request model for creating a feedback
 */
export interface FeedbackCreate {
  feedback_type: FeedbackType;
  objective: string;
  instructions: string;
  constraints: string;
  context: string;
  output_format?: string;
}

/**
 * Request model for updating a feedback
 */
export interface FeedbackUpdate {
  feedback_type?: FeedbackType;
  objective?: string;
  instructions?: string;
  constraints?: string;
  context?: string;
  output_format?: string;
}

