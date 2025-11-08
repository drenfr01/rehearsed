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
    studentResponses: string[];
    inlineFeedback: string[];
    summaryFeedback: string;
    summary: string;
    answeringStudent: number;
    appropriateResponse: boolean;
    appropriateExplanation: string;
    learningGoalsAchieved: boolean;
}

export interface ChatResponse {
    messages: Message[];
    studentResponses: string[];
    inlineFeedback: string[];
    summaryFeedback: string;
    summary: string;
    answeringStudent: number;
    appropriateResponse: boolean;
    appropriateExplanation: string;
    learningGoalsAchieved: boolean;
}