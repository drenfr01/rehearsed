import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ScenarioService } from '../../core/services/scenario.service';
import { Scenario } from '../../core/models/scenario.model';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { Router } from '@angular/router';

@Component({
  selector: 'app-scenario-selection',
  imports: [
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    CommonModule,
    LoadingSpinner,
  ],
  templateUrl: './scenario-selection.html',
  styleUrl: './scenario-selection.css',
})
export class ScenarioSelection {
  protected isLoading = signal(false);
  protected error = signal<string>('');
  private scenarioService = inject(ScenarioService);
  protected scenarios = this.scenarioService.loadedScenarios;
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);
  form = new FormGroup({
    selectedScenario: new FormControl<Scenario | null>(null, [Validators.required]),
  });

  ngOnInit() {
    this.isLoading.set(true);
    const subscription = this.scenarioService.getScenarios().subscribe({
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }

  get selectedScenario(): Scenario | null {
    return this.form.get('selectedScenario')?.value || null;
  }

  onSubmit() {
    if (this.form.invalid) return;
    
    const selectedScenario = this.form.value.selectedScenario;
    if (selectedScenario) {
      this.isLoading.set(true)
      const subscription = this.scenarioService.setCurrentScenario(selectedScenario.id).subscribe({
        error: (error: Error) => {
          this.error.set(error.message);
          this.isLoading.set(false);
        },
        complete: () => {
          this.isLoading.set(false);
          this.router.navigate(['/app/scenario-overview'], { replaceUrl: true });
        },
      });

      this.destroyRef.onDestroy(() => {
        subscription.unsubscribe();
      });
    }
  }
}
