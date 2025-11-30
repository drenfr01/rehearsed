export type role = "user" | "assistant" 

export interface Message {
    role: role;
    content: string;
    student_name?: string;
    audio_base64?: string;
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
}

export interface StudentResponse {
    student_response: string;
    student_details: Agent;
    student_personality: AgentPersonality;
    audio_base64: string;
}

export interface ChatResponse {
    messages: Message[];
    interrupt_task: string;
    interrupt_value: string;
    interrupt_value_type: 'text' | 'image' | 'audio' | 'video';
    student_responses: StudentResponse[];
    inline_feedback: string[];
    summary_feedback: string;
    summary: string;
    answering_student: number;
    appropriate_response: boolean;
    appropriate_explanation: string;
    learning_goals_achieved: boolean;
    interrupt: object[];
}