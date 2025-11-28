import { Routes } from '@angular/router';
import { authGuard } from './core/services/auth-guard';
import { Login } from './features/login/login.component';
import { Register } from './features/register/register.component';
import { ScenarioSelection } from './features/scenario-selection/scenario-selection';
import { ScenarioOverview } from './features/scenario-overview/scenario-overview';
import { Classroom } from './features/classroom/classroom';
import { ScenarioFeedback } from './features/scenario-feedback/scenario-feedback';
import { Admin } from './features/admin/admin';
import { AdminAgentPersonalities } from './features/admin-agent-personalities/admin-agent-personalities';
import { AdminAgents } from './features/admin-agents/admin-agents';
import { AdminScenarios } from './features/admin-scenarios/admin-scenarios';
import { AdminFeedback } from './features/admin-feedback/admin-feedback';

export const routes: Routes = [
    {
        path: '',
        component: Login,
    },
    {
        path: 'register',
        component: Register,
    },
    {
        path: 'app',
        canMatch: [authGuard],
        children: [
            {
                path: 'scenario-selection',
                component: ScenarioSelection,
            },
            {
                path: 'scenario-overview',
                component: ScenarioOverview,
            },
            {
                path: 'classroom', 
                component: Classroom,
            },
            {
                path: 'scenario-feedback',
                component: ScenarioFeedback,
            },
            {
                path: 'admin',
                component: Admin,
            },
            {
                path: 'admin/agent-personalities',
                component: AdminAgentPersonalities,
            },
            {
                path: 'admin/agents',
                component: AdminAgents,
            },
            {
                path: 'admin/scenarios',
                component: AdminScenarios,
            },
            {
                path: 'admin/feedback',
                component: AdminFeedback,
            }
        ]
    }
];
