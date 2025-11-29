import { Component, DestroyRef, inject, signal, computed } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ScenarioService } from '../../core/services/scenario.service';
import { UserContentService } from '../../core/services/user-content.service';
import { Scenario } from '../../core/models/scenario.model';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
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
    MatIconModule,
    MatTooltipModule,
    MatSnackBarModule,
    CommonModule,
    LoadingSpinner,
  ],
  templateUrl: './scenario-selection.html',
  styleUrl: './scenario-selection.css',
})
export class ScenarioSelection {
  protected isLoading = signal(false);
  protected isCopying = signal(false);
  protected error = signal<string>('');
  private scenarioService = inject(ScenarioService);
  private userContentService = inject(UserContentService);
  private snackBar = inject(MatSnackBar);
  protected allScenarios = signal<Scenario[]>([]);
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);
  
  // Computed signals for global and local scenarios
  protected globalScenarios = computed(() => 
    this.allScenarios().filter(s => s.is_global === true || s.owner_id === null)
  );
  protected myScenarios = computed(() => 
    this.allScenarios().filter(s => s.is_global === false && s.owner_id !== null)
  );
  
  form = new FormGroup({
    selectedScenario: new FormControl<Scenario | null>(null, [Validators.required]),
  });

  ngOnInit() {
    this.loadScenarios();
  }

  loadScenarios() {
    this.isLoading.set(true);
    const subscription = this.scenarioService.getScenarios().subscribe({
      next: (scenarios) => {
        this.allScenarios.set(scenarios);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.error.set(error.message);
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

  copyToMyScenarios(scenario: Scenario) {
    this.isCopying.set(true);
    const subscription = this.userContentService.copyGlobalScenario(scenario.id).subscribe({
      next: (newScenario) => {
        this.snackBar.open(`Copied "${scenario.name}" to My Scenarios`, 'Close', { duration: 3000 });
        // Reload scenarios to include the new copy
        this.loadScenarios();
        this.isCopying.set(false);
      },
      error: (error) => {
        console.error('Failed to copy scenario', error);
        const errorMessage = error.error?.detail || 'Failed to copy scenario';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        this.isCopying.set(false);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
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
