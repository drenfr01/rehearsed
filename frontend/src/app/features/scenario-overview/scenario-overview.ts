import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { Message } from '../../core/models/chat-graph.model';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { ScenarioService } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-overview',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
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
  private scenarioService = inject(ScenarioService);

  form = new FormGroup({
    scenarioId: new FormControl(this.scenarioService.loadedCurrentScenario()?.id, [Validators.required]),
    scenarioName: new FormControl(this.scenarioService.loadedCurrentScenario()?.name, [Validators.required]),
    scenarioDescription: new FormControl(this.scenarioService.loadedCurrentScenario()?.overview, [Validators.required]),
    initialPrompt: new FormControl('We started with the line y = 2/5 x + 1. What do we know about a second line if the system has one solution?', [Validators.required]),
  });

  onSubmit() {
    if (this.form.invalid) return;
    
    this.isLoading.set(true);
    this.error.set('');
    
    const newMessage: Message = {
      role: 'user',
      content: this.form.value.initialPrompt!,
    }
    
    // Sending initial graph request, hence the true flag
    const subscription = this.chatGraphService.sendGraphRequest({
        messages: [newMessage],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
    }, true).subscribe({
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
        this.router.navigate(['/app/classroom']);
      },
    });
      
  }
}
