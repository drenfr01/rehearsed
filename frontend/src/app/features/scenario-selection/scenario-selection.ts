import { Component, DestroyRef, inject, signal } from '@angular/core';
import { ScenarioService } from '../../core/services/scenario.service';

@Component({
  selector: 'app-scenario-selection',
  imports: [],
  templateUrl: './scenario-selection.html',
  styleUrl: './scenario-selection.css',
})
export class ScenarioSelection {
  protected isLoading = signal(false);
  protected error = signal<string>('');
  private scenarioService = inject(ScenarioService);
  private destroyRef = inject(DestroyRef);

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

  onSubmit() {
    console.log('Submitted');
  }
}
