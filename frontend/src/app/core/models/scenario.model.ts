export interface Scenario {
    id: number;
    name: string;
    description: string;
    overview: string;
    system_instructions: string;
    initial_prompt: string;
    teaching_objectives: string;
    created_at?: string;
    owner_id?: number | null;
    is_global?: boolean;
}

export interface ScenarioCreate {
    name: string;
    description: string;
    overview: string;
    system_instructions: string;
    initial_prompt: string;
    teaching_objectives: string;
}

export interface ScenarioUpdate {
    name?: string;
    description?: string;
    overview?: string;
    system_instructions?: string;
    initial_prompt?: string;
    teaching_objectives?: string;
}
