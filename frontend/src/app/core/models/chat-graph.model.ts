export type role = "user" | "assistant" 

export interface Message {
    role: role;
    content: string;
}

export interface ChatRequest {
    messages: Message[];
    is_resumption: boolean;
    resumption_text: string;
    resumption_approved: boolean;
}

export interface ChatResponse {
    messages: Message[];
    interrupt_task: string;
    interrupt_value: string;
    interrupt_value_type: 'text' | 'image' | 'audio' | 'video';
}