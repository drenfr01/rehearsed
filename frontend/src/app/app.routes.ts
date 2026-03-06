import { Routes } from '@angular/router';
import { authGuard } from './core/services/auth-guard';
import { Login } from './features/login/login.component';
import { Register } from './features/register/register.component';
import { ScenarioSelection } from './features/scenario-selection/scenario-selection';
import { ScenarioOverview } from './features/scenario-overview/scenario-overview';
import { Classroom } from './features/classroom/classroom';
import { ScenarioFeedback } from './features/scenario-feedback/scenario-feedback';
import { OneOnOneSetup } from './features/one-on-one-setup/one-on-one-setup';
import { OneOnOneConversation } from './features/one-on-one-conversation/one-on-one-conversation';
import { Admin } from './features/admin/admin';
import { AdminAgentPersonalities } from './features/admin-agent-personalities/admin-agent-personalities';
import { AdminAgents } from './features/admin-agents/admin-agents';
import { AdminScenarios } from './features/admin-scenarios/admin-scenarios';
import { AdminFeedback } from './features/admin-feedback/admin-feedback';
import { AdminAppConfig } from './features/admin-app-config/admin-app-config';
import { UserContent } from './features/user-content/user-content';
import { UserScenarios } from './features/user-scenarios/user-scenarios';
import { UserAgents } from './features/user-agents/user-agents';
import { UserPersonalities } from './features/user-personalities/user-personalities';
import { UserFeedback } from './features/user-feedback/user-feedback';

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
                path: 'one-on-one-setup',
                component: OneOnOneSetup,
            },
            {
                path: 'one-on-one',
                component: OneOnOneConversation,
            },
            // User Content Routes
            {
                path: 'my-content',
                component: UserContent,
            },
            {
                path: 'my-content/scenarios',
                component: UserScenarios,
            },
            {
                path: 'my-content/agents',
                component: UserAgents,
            },
            {
                path: 'my-content/personalities',
                component: UserPersonalities,
            },
            {
                path: 'my-content/feedback',
                component: UserFeedback,
            },
            // Admin Routes
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
            },
            {
                path: 'admin/app-config',
                component: AdminAppConfig,
            }
        ]
    }
];
