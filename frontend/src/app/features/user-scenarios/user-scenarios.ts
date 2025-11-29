import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { UserContentService } from '../../core/services/user-content.service';
import { Scenario, ScenarioCreate } from '../../core/models/scenario.model';
import { EditScenarioDialog, EditScenarioDialogData, EditScenarioDialogResult } from '../../shared/dialogs/edit-scenario-dialog/edit-scenario-dialog';

@Component({
  selector: 'app-user-scenarios',
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    LoadingSpinner,
  ],
  templateUrl: './user-scenarios.html',
  styleUrl: './user-scenarios.css',
})
export class UserScenarios implements OnInit {
  private userContentService = inject(UserContentService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  scenarios = signal<Scenario[]>([]);
  displayedColumns: string[] = ['id', 'name', 'description', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);

  createScenarioForm: FormGroup;

  constructor() {
    this.createScenarioForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      description: ['', [Validators.required, Validators.minLength(10)]],
      overview: ['', [Validators.required, Validators.minLength(10)]],
      system_instructions: ['', [Validators.required, Validators.minLength(10)]],
      initial_prompt: ['', [Validators.required, Validators.minLength(5)]],
    });
  }

  ngOnInit() {
    this.loadScenarios();
  }

  loadScenarios() {
    this.isLoading.set(true);
    const subscription = this.userContentService.getMyScenarios().subscribe({
      next: (scenarios) => {
        this.scenarios.set(scenarios);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load scenarios', error);
        this.snackBar.open('Failed to load scenarios', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  toggleCreateForm() {
    this.showCreateForm.set(!this.showCreateForm());
    if (!this.showCreateForm()) {
      this.createScenarioForm.reset();
    }
  }

  createScenario() {
    if (this.createScenarioForm.valid) {
      const scenarioData: ScenarioCreate = this.createScenarioForm.value;
      const subscription = this.userContentService.createScenario(scenarioData).subscribe({
        next: (scenario) => {
          this.scenarios.update(scenarios => [...scenarios, scenario]);
          this.snackBar.open('Scenario created successfully', 'Close', { duration: 3000 });
          this.createScenarioForm.reset();
          this.showCreateForm.set(false);
        },
        error: (error) => {
          console.error('Failed to create scenario', error);
          const errorMessage = error.error?.detail || 'Failed to create scenario';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  openEditDialog(scenario: Scenario) {
    const dialogData: EditScenarioDialogData = { scenario };
    const dialogRef = this.dialog.open(EditScenarioDialog, {
      width: '700px',
      maxHeight: '90vh',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result: EditScenarioDialogResult | undefined) => {
      if (result) {
        this.saveEdit(scenario.id, result);
      }
    });
  }

  private saveEdit(scenarioId: number, data: EditScenarioDialogResult) {
    const subscription = this.userContentService.updateScenario(scenarioId, data).subscribe({
      next: (updatedScenario) => {
        this.scenarios.update(scenarios => 
          scenarios.map(s => s.id === scenarioId ? updatedScenario : s)
        );
        this.snackBar.open('Scenario updated successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to update scenario', error);
        const errorMessage = error.error?.detail || 'Failed to update scenario';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  deleteScenario(scenarioId: number, name: string) {
    if (confirm(`Are you sure you want to delete scenario "${name}"?`)) {
      const subscription = this.userContentService.deleteScenario(scenarioId).subscribe({
        next: () => {
          this.scenarios.update(scenarios => scenarios.filter(s => s.id !== scenarioId));
          this.snackBar.open('Scenario deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to delete scenario', error);
          const errorMessage = error.error?.detail || 'Failed to delete scenario';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }
}

