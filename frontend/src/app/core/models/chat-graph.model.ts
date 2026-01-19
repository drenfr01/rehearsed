export type role = "user" | "assistant" 

export interface Message {
    role: role;
    content: string;
    student_name?: string;
    audio_base64?: string;
    audio_id?: string;
}

export interface Agent {
    id: string;
    name: string;
    objective: string;
    instructions: string;
    constraints: string;
}

export interface AgentPersonality {
    id: string;
    name: string;
    personality_description: string;
}

export interface ChatRequest {
    messages: Message[];
    is_resumption: boolean;
    resumption_text: string;
    resumption_approved: boolean;
    audio_base64?: string;
}

export interface StudentResponse {
    student_response: string;
    student_details: Agent;
    student_personality: AgentPersonality;
    audio_base64: string;
    audio_id?: string;
}

export interface SummaryFeedbackResponse {
    lesson_summary: string;
    key_moments: string;
    overall_feedback: string;
    your_strengths: string;
    areas_for_growth: string;
    next_steps: string;
    celebration: string;
}

export interface ChatResponse {
    messages: Message[];
    interrupt_task: string;
    interrupt_value: string;
    interrupt_value_type: 'text' | 'image' | 'audio' | 'video';
    student_responses: StudentResponse[];
    inline_feedback: string[];
    summary_feedback: SummaryFeedbackResponse | string;
    summary: string;
    answering_student: number;
    appropriate_response: boolean;
    appropriate_explanation: string;
    learning_goals_achieved: boolean;
    transcribed_text: string;
    interrupt: object[];
}