import { Component, computed, inject, input, OnInit, signal, DestroyRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Agent } from '../../../core/models/agent.model';
import { Message } from '../../../core/models/chat-graph.model';
import { ScenarioService } from '../../../core/services/scenario.service';

export interface StudentStatus {
  agent: Agent;
  messageCount: number;
}

@Component({
  selector: 'app-classroom-status',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './classroom-status.html',
  styleUrl: './classroom-status.css',
})
export class ClassroomStatus implements OnInit {
  private scenarioService = inject(ScenarioService);
  private destroyRef = inject(DestroyRef);

  // Input: current messages from the classroom
  messages = input<Message[]>([]);
  
  // Internal state for agents
  protected agents = signal<Agent[]>([]);
  protected isLoading = signal<boolean>(true);
  protected error = signal<string>('');

  // Computed: map of student name -> message count
  protected studentMessageCounts = computed(() => {
    const messages = this.messages();
    const counts = new Map<string, number>();
    
    for (const message of messages) {
      if (message.role === 'assistant' && message.student_name) {
        const current = counts.get(message.student_name) || 0;
        counts.set(message.student_name, current + 1);
      }
    }
    
    return counts;
  });

  // Computed: student statuses with message counts
  protected studentStatuses = computed<StudentStatus[]>(() => {
    const agents = this.agents();
    const counts = this.studentMessageCounts();
    
    return agents.map(agent => ({
      agent,
      messageCount: counts.get(agent.name) || 0,
    }));
  });

  ngOnInit() {
    this.loadAgents();
  }

  private loadAgents() {
    const currentScenario = this.scenarioService.loadedCurrentScenario();
    if (!currentScenario) {
      this.error.set('No scenario selected');
      this.isLoading.set(false);
      return;
    }

    const subscription = this.scenarioService.getAgentsByScenario(currentScenario.id).subscribe({
      next: (agents) => {
        this.agents.set(agents);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load agents:', err);
        this.error.set('Failed to load students');
        this.isLoading.set(false);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }

  // Get icon for student based on their index
  getStudentIcon(index: number): string {
    return 'smart_toy'
  }

  // Get a color class based on the agent's display_text_color
  getColorClass(displayTextColor: string | undefined): string {
    if (!displayTextColor) {
      return 'student-teal'; // default
    }
    
    const colorMap: Record<string, string> = {
      'teal': 'student-teal',
      'light purple': 'student-light-purple',
      'dark purple': 'student-dark-purple',
      'mustard': 'student-mustard',
      'light blue': 'student-light-blue',
      'coral': 'student-coral',
    };
    
    return colorMap[displayTextColor.toLowerCase()] || 'student-teal';
  }
}

