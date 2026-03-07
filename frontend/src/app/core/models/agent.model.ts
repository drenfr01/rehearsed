export interface AgentVoice {
    id: number;
    voice_name: string;
}

export interface Avatar {
    id: number;
    name: string;
    file_path: string;
}

export interface AgentPersonality {
    id: number;
    name: string;
    personality_description: string;
    created_at?: string;
    owner_id?: number | null;
    is_global?: boolean;
}

export interface AgentPersonalityCreate {
    name: string;
    personality_description: string;
}

export interface AgentPersonalityUpdate {
    name?: string;
    personality_description?: string;
}

export interface Agent {
    id: string;
    name: string;
    scenario_id: number;
    agent_personality_id: number;
    voice: string;
    display_text_color: string;
    avatar_gcs_uri?: string;
    objective: string;
    instructions: string;
    constraints: string;
    context: string;
    created_at?: string;
    agent_personality?: AgentPersonality;
    owner_id?: number | null;
    is_global?: boolean;
}

export interface AgentCreate {
    id: string;
    name: string;
    scenario_id: number;
    agent_personality_id: number;
    voice?: string;
    display_text_color?: string;
    avatar_gcs_uri?: string;
    objective?: string;
    instructions?: string;
    constraints?: string;
    context?: string;
}

export interface AgentUpdate {
    name?: string;
    scenario_id?: number;
    agent_personality_id?: number;
    voice?: string;
    display_text_color?: string;
    avatar_gcs_uri?: string;
    objective?: string;
    instructions?: string;
    constraints?: string;
    context?: string;
}

