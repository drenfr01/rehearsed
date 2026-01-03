import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Footer } from "./Footer";
import { Clock, Users, Target } from "lucide-react";
import logo from "figma:asset/12b39b0f5302eae32092715fdb2e4a6a0eab7bd3.png";
import { useState } from "react";
import { AdminDashboard } from "./AdminDashboard";
import { scenarioData } from "../../data/scenarios";

/**
 * ANGULAR MIGRATION NOTE:
 * This component translates to a ScenarioSelectionComponent
 * - Scenario data would come from ScenarioService.getAll()
 * - View state managed by Angular Router (separate routes for scenarios vs admin)
 */

interface SimulationSelectionPageProps {
  onSelectSimulation: (id: string) => void;
  onLogout: () => void;
  onNavigateToOverview?: () => void;
  onNavigateToClassroom?: () => void;
  onNewSession?: () => void;
}

export function SimulationSelectionPage({ onSelectSimulation, onLogout, onNavigateToOverview, onNavigateToClassroom, onNewSession }: SimulationSelectionPageProps) {
  const [currentView, setCurrentView] = useState<"scenarios" | "admin">("scenarios");
  
  // Angular: This would come from ScenarioService via Observable
  const simulations = Object.values(scenarioData).map(scenario => ({
    id: scenario.id,
    title: scenario.title,
    description: scenario.description,
    duration: scenario.duration.replace(' minutes', ' min'),
    students: scenario.students.length,
    category: scenario.category,
    difficulty: scenario.difficulty
  }));
  
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "Beginner": return "bg-green-100 text-green-800";
      case "Intermediate": return "bg-yellow-100 text-yellow-800";
      case "Advanced": return "bg-red-100 text-red-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  // Show Admin Dashboard if that view is selected
  if (currentView === "admin") {
    return (
      <AdminDashboard 
        onLogout={onLogout} 
        onBackToScenarios={() => setCurrentView("scenarios")}
        onNavigateToOverview={onNavigateToOverview}
        onNavigateToClassroom={onNavigateToClassroom}
        onNewSession={onNewSession}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-background-page)] flex flex-col" data-layer="scenario-selection-page">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10" data-layer="page-header">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between" data-layer="header-content">
          <div className="flex items-center gap-6" data-layer="header-left-section">
            <img src={logo} alt="RehearseSR" className="h-10" data-layer="brand-logo" />
            
            {/* Tab Navigation */}
            <div className="flex gap-2" data-layer="tab-navigation">
              <Button
                onClick={() => setCurrentView("scenarios")}
                variant="default"
                size="sm"
                className="bg-[var(--color-brand-teal-primary)] hover:bg-[var(--color-brand-teal-primary-hover)] text-white"
                data-layer="tab-button-active"
              >
                Scenario Selection
              </Button>
              {onNavigateToOverview && (
                <Button
                  onClick={onNavigateToOverview}
                  variant="outline"
                  size="sm"
                  className="bg-white hover:bg-gray-100 text-gray-700"
                  data-layer="tab-button"
                >
                  Scenario Overview
                </Button>
              )}
              {onNavigateToClassroom && (
                <Button
                  onClick={onNavigateToClassroom}
                  variant="outline"
                  size="sm"
                  className="bg-white hover:bg-gray-100 text-gray-700"
                  data-layer="tab-button"
                >
                  Scenario Classroom
                </Button>
              )}
              <Button
                onClick={() => setCurrentView("admin")}
                variant="outline"
                size="sm"
                className="bg-white hover:bg-gray-100 text-gray-700"
                data-layer="tab-button"
              >
                Admin Dashboard
              </Button>
            </div>
          </div>
          
          <div className="flex gap-2" data-layer="header-right-section">
            {onNewSession && (
              <Button 
                variant="outline" 
                onClick={onNewSession}
                size="sm"
                className="bg-white hover:bg-gray-100 text-gray-700"
                data-layer="new-session-button"
              >
                New Session
              </Button>
            )}
            <Button 
              variant="outline" 
              onClick={onLogout}
              size="sm"
              className="bg-[var(--color-brand-teal-signout)] text-white hover:bg-[var(--color-brand-teal-primary-hover)] border-[var(--color-brand-teal-signout)]"
              data-layer="sign-out-button"
            >
              Sign Out
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-layer="page-main-content">
        <div className="mb-6" data-layer="welcome-section">
          <h2 className="text-gray-900 mb-2" data-layer="welcome-heading">Welcome Back, Teacher!</h2>
          <p className="text-gray-600" data-layer="welcome-description">Select a simulation to practice your teaching discourse moves</p>
        </div>

        {/* Simulations Grid */}
        <div className="flex flex-wrap gap-6" data-layer="scenario-cards-container">
          {simulations.map((sim) => (
            <Card key={sim.id} className="p-6 hover:shadow-lg transition-shadow flex-1 min-w-[calc(50%-12px)]" data-layer="scenario-card">
              <div className="flex flex-col h-full" data-layer="scenario-card-content">
                <div className="flex items-start justify-between mb-3" data-layer="scenario-card-header">
                  <h3 className="text-gray-900 flex-1" data-layer="scenario-title">{sim.title}</h3>
                  <Badge className={getDifficultyColor(sim.difficulty)} data-layer="difficulty-badge">
                    {sim.difficulty}
                  </Badge>
                </div>

                <p className="text-gray-600 mb-4 flex-1" data-layer="scenario-description">{sim.description}</p>

                <div className="flex items-center gap-4 mb-4 text-sm text-gray-500" data-layer="scenario-metadata">
                  <div className="flex items-center gap-1" data-layer="metadata-duration">
                    <Clock className="w-4 h-4" />
                    <span>{sim.duration}</span>
                  </div>
                  <div className="flex items-center gap-1" data-layer="metadata-students">
                    <Users className="w-4 h-4" />
                    <span>{sim.students} students</span>
                  </div>
                  <div className="flex items-center gap-1" data-layer="metadata-category">
                    <Target className="w-4 h-4" />
                    <span>{sim.category}</span>
                  </div>
                </div>

                <Button 
                  onClick={() => onSelectSimulation(sim.id)}
                  className="w-full bg-[var(--color-brand-purple)] hover:bg-[var(--color-brand-purple-hover)] text-white"
                  data-layer="view-details-button"
                >
                  View Details
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}