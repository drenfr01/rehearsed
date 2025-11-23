export interface Scenario {
    id: number;
    name: string;
    description: string;
    overview: string;
    system_instructions: string;
    initial_prompt: string;
    created_at?: string;
}

export interface ScenarioCreate {
    name: string;
    description: string;
    overview: string;
    system_instructions: string;
    initial_prompt: string;
}
