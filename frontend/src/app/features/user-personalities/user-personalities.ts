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
import { AgentPersonality, AgentPersonalityCreate } from '../../core/models/agent.model';
import { EditPersonalityDialog, EditPersonalityDialogData, EditPersonalityDialogResult } from '../../shared/dialogs/edit-personality-dialog/edit-personality-dialog';

@Component({
  selector: 'app-user-personalities',
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
  templateUrl: './user-personalities.html',
  styleUrl: './user-personalities.css',
})
export class UserPersonalities implements OnInit {
  private userContentService = inject(UserContentService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  personalities = signal<AgentPersonality[]>([]);
  displayedColumns: string[] = ['id', 'name', 'personality_description', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);

  createPersonalityForm: FormGroup;

  constructor() {
    this.createPersonalityForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      personality_description: ['', [Validators.required, Validators.minLength(10)]],
    });
  }

  ngOnInit() {
    this.loadPersonalities();
  }

  loadPersonalities() {
    this.isLoading.set(true);
    const subscription = this.userContentService.getMyAgentPersonalities().subscribe({
      next: (personalities) => {
        this.personalities.set(personalities);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load agent personalities', error);
        this.snackBar.open('Failed to load agent personalities', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  toggleCreateForm() {
    this.showCreateForm.set(!this.showCreateForm());
    if (!this.showCreateForm()) {
      this.createPersonalityForm.reset();
    }
  }

  createPersonality() {
    if (this.createPersonalityForm.valid) {
      const personalityData: AgentPersonalityCreate = this.createPersonalityForm.value;
      const subscription = this.userContentService.createAgentPersonality(personalityData).subscribe({
        next: (personality) => {
          this.personalities.update(personalities => [...personalities, personality]);
          this.snackBar.open('Agent personality created successfully', 'Close', { duration: 3000 });
          this.createPersonalityForm.reset();
          this.showCreateForm.set(false);
        },
        error: (error) => {
          console.error('Failed to create agent personality', error);
          const errorMessage = error.error?.detail || 'Failed to create agent personality';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  openEditDialog(personality: AgentPersonality) {
    const dialogData: EditPersonalityDialogData = { personality };
    const dialogRef = this.dialog.open(EditPersonalityDialog, {
      width: '600px',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result: EditPersonalityDialogResult | undefined) => {
      if (result) {
        this.saveEdit(personality.id, result);
      }
    });
  }

  private saveEdit(personalityId: number, data: EditPersonalityDialogResult) {
    const subscription = this.userContentService.updateAgentPersonality(personalityId, data).subscribe({
      next: (updatedPersonality) => {
        this.personalities.update(personalities => 
          personalities.map(p => p.id === personalityId ? updatedPersonality : p)
        );
        this.snackBar.open('Agent personality updated successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to update agent personality', error);
        const errorMessage = error.error?.detail || 'Failed to update agent personality';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  deletePersonality(personalityId: number, name: string) {
    if (confirm(`Are you sure you want to delete agent personality "${name}"?`)) {
      const subscription = this.userContentService.deleteAgentPersonality(personalityId).subscribe({
        next: () => {
          this.personalities.update(personalities => personalities.filter(p => p.id !== personalityId));
          this.snackBar.open('Agent personality deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to delete agent personality', error);
          const errorMessage = error.error?.detail || 'Failed to delete agent personality';
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

