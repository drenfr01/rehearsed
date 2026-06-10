// Types are generated from the backend OpenAPI spec via HeyAPI (npm run generate:api).
import type { AgentLlmConfigResponse, AgentLlmConfigUpdateRequest } from '../api';

export type { LlmModelResponse as LlmModel } from '../api';

// The backend types agent_type as a plain string; the frontend narrows it to
// the known agent types for stricter UI handling.
export type AgentType = 'student_agent' | 'student_choice_agent' | 'inline_feedback' | 'summary_feedback';

export type AgentLlmConfig = AgentLlmConfigResponse & { agent_type: AgentType };

export type AgentLlmConfigUpdate = AgentLlmConfigUpdateRequest & { agent_type: AgentType };
