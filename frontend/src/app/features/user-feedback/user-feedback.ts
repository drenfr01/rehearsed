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
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { UserContentService } from '../../core/services/user-content.service';
import { ScenarioService } from '../../core/services/scenario.service';
import { Feedback, FeedbackCreate, FeedbackType } from '../../core/models/feedback.model';
import { Scenario } from '../../core/models/scenario.model';
import { EditFeedbackDialog, EditFeedbackDialogData, EditFeedbackDialogResult } from '../../shared/dialogs/edit-feedback-dialog/edit-feedback-dialog';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-user-feedback',
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
    MatSelectModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatChipsModule,
    LoadingSpinner,
  ],
  templateUrl: './user-feedback.html',
  styleUrl: './user-feedback.css',
})
export class UserFeedback implements OnInit {
  private userContentService = inject(UserContentService);
  private scenarioService = inject(ScenarioService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  feedbacks = signal<Feedback[]>([]);
  scenarios = signal<Scenario[]>([]);
  displayedColumns: string[] = ['id', 'feedback_type', 'scenario', 'objective', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);
  feedbackTypes: FeedbackType[] = ['inline', 'summary'];

  createFeedbackForm: FormGroup;

  constructor() {
    this.createFeedbackForm = this.fb.group({
      feedback_type: ['inline', [Validators.required]],
      scenario_id: [null, [Validators.required]],
      objective: ['', [Validators.required, Validators.minLength(1)]],
      instructions: ['', [Validators.required, Validators.minLength(1)]],
      constraints: ['', [Validators.required, Validators.minLength(1)]],
      context: ['', [Validators.required, Validators.minLength(1)]],
      output_format: [''],
    });
  }

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading.set(true);
    
    const subscription = forkJoin({
      feedbacks: this.userContentService.getMyFeedback(),
      scenarios: this.scenarioService.getScenarios(),
    }).subscribe({
      next: (data) => {
        this.feedbacks.set(data.feedbacks);
        this.scenarios.set(data.scenarios);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load data', error);
        this.snackBar.open('Failed to load data', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });

    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  toggleCreateForm() {
    this.showCreateForm.set(!this.showCreateForm());
    if (!this.showCreateForm()) {
      this.createFeedbackForm.reset({ feedback_type: 'inline', scenario_id: null });
    }
  }

  createFeedback() {
    if (this.createFeedbackForm.valid) {
      const feedbackData: FeedbackCreate = this.createFeedbackForm.value;
      const subscription = this.userContentService.createFeedback(feedbackData).subscribe({
        next: (feedback) => {
          this.feedbacks.update(feedbacks => [...feedbacks, feedback]);
          this.snackBar.open('Feedback created successfully', 'Close', { duration: 3000 });
          this.createFeedbackForm.reset({ feedback_type: 'inline', scenario_id: null });
          this.showCreateForm.set(false);
        },
        error: (error) => {
          console.error('Failed to create feedback', error);
          const errorMessage = error.error?.detail || 'Failed to create feedback';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  openEditDialog(feedback: Feedback) {
    const dialogData: EditFeedbackDialogData = {
      feedback,
      scenarios: this.scenarios(),
    };
    const dialogRef = this.dialog.open(EditFeedbackDialog, {
      width: '800px',
      maxHeight: '90vh',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result: EditFeedbackDialogResult | undefined) => {
      if (result) {
        this.saveEdit(feedback.id, result);
      }
    });
  }

  private saveEdit(feedbackId: number, data: EditFeedbackDialogResult) {
    const subscription = this.userContentService.updateFeedback(feedbackId, data).subscribe({
      next: (updatedFeedback) => {
        this.feedbacks.update(feedbacks => 
          feedbacks.map(f => f.id === feedbackId ? updatedFeedback : f)
        );
        this.snackBar.open('Feedback updated successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to update feedback', error);
        const errorMessage = error.error?.detail || 'Failed to update feedback';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  deleteFeedback(feedbackId: number, feedbackType: FeedbackType) {
    if (confirm(`Are you sure you want to delete the "${feedbackType}" feedback?`)) {
      const subscription = this.userContentService.deleteFeedback(feedbackId).subscribe({
        next: () => {
          this.feedbacks.update(feedbacks => feedbacks.filter(f => f.id !== feedbackId));
          this.snackBar.open('Feedback deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to delete feedback', error);
          const errorMessage = error.error?.detail || 'Failed to delete feedback';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  getFeedbackTypeLabel(type: FeedbackType): string {
    return type === 'inline' ? 'Inline' : 'Summary';
  }

  truncateText(text: string, maxLength: number = 100): string {
    if (!text) return '-';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }

  getScenarioName(scenarioId: number): string {
    const scenario = this.scenarios().find(s => s.id === scenarioId);
    return scenario?.name || 'Unknown';
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }
}

