import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { Message } from '../../core/models/chat-graph.model';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-scenario-overview',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    CommonModule,
  ],
  templateUrl: './scenario-overview.html',
  styleUrl: './scenario-overview.css',
})
export class ScenarioOverview {
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private chatGraphService = inject(ChatGraphService);
  protected isLoading = signal(false);
  protected error = signal<string>('');
  private scenarioOverviewValue = `You are an 8th grade mathematics teacher in the middle of a Systems of Linear Equations unit.
    You gave the following task to your students:
    Consider the equation y = 2/5 x + 1 . Write a second linear equation to create a system of linear equations with only one solution.
    You wrote the following learning objectives for your students to meet after engaging with and discussing this task:
    Students will create a system of linear equations with one solution by identifying a line with a different slope than the original line.
    Students will describe why two linear equations must have different slopes to make a system with exactly one solution.
    You are about to facilitate a full group discussion about this task. Your goal is to sequence students' ideas and thinking by using mathematical questions to guide students to meet these learning objectives.
    You have decided to use the following student work to do this.`;

  form = new FormGroup({
    scenarioId: new FormControl('', [Validators.required]),
    scenarioName: new FormControl('', [Validators.required]),
    scenarioDescription: new FormControl('', [Validators.required]),
    initialPrompt: new FormControl(this.scenarioOverviewValue, [Validators.required]),
  });

  onSubmit() {
    if (this.form.invalid) return;
    
    this.isLoading.set(true);
    this.error.set('');
    
    const newMessage: Message = {
      role: 'user',
      content: this.form.value.initialPrompt!,
    }
    
    try {
      // Sending initial graph request, hence the true flag
      this.chatGraphService.sendGraphRequest({
        messages: [newMessage],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
      }, true);
      
      // Navigate to the next page after successful submission
      this.router.navigate(['/app/classroom']);
    } catch (err) {
      this.error.set('Failed to submit scenario. Please try again.');
    } finally {
      this.isLoading.set(false);
    }
  }
}
