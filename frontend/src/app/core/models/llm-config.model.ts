export type AgentType = 'student_agent' | 'student_choice_agent' | 'inline_feedback' | 'summary_feedback';

export interface LlmModel {
  id: number;
  name: string;
}

export interface AgentLlmConfig {
  agent_type: AgentType;
  llm_model_id: number;
  llm_model_name: string;
}

export interface AgentLlmConfigUpdate {
  agent_type: AgentType;
  llm_model_id: number;
}
