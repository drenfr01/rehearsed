export interface AgentPersonality {
    id: number;
    name: string;
    personality_description: string;
    created_at?: string;
}

export interface AgentPersonalityCreate {
    name: string;
    personality_description: string;
}

export interface Agent {
    id: string;
    name: string;
    scenario_id: number;
    agent_personality_id: number;
    voice: string;
    display_text_color: string;
    objective: string;
    instructions: string;
    constraints: string;
    context: string;
    created_at?: string;
    agent_personality?: AgentPersonality;
}

export interface AgentCreate {
    id: string;
    name: string;
    scenario_id: number;
    agent_personality_id: number;
    voice?: string;
    display_text_color?: string;
    objective?: string;
    instructions?: string;
    constraints?: string;
    context?: string;
}

