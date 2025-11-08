import { Routes } from '@angular/router';
import { authGuard } from './core/services/auth-guard';
import { Login } from './features/login/login.component';
import { ScenarioSelection } from './features/scenario-selection/scenario-selection';
import { ScenarioOverview } from './features/scenario-overview/scenario-overview';
import { Classroom } from './features/classroom/classroom';

export const routes: Routes = [
    {
        path: '',
        component: Login,
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
            }
            {
                path: 'classroom', 
                component: Classroom,
            }
        ]
    }
];
