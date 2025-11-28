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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { AdminService } from '../../core/services/admin.service';
import { User, UserCreate } from '../../core/models/user.model';
import { EditUserDialog, EditUserDialogData, EditUserDialogResult } from '../../shared/dialogs/edit-user-dialog/edit-user-dialog';

@Component({
  selector: 'app-admin',
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
    MatSlideToggleModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    LoadingSpinner,
  ],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class Admin implements OnInit {
  private adminService = inject(AdminService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  users = signal<User[]>([]);
  pendingUsers = signal<User[]>([]);
  displayedColumns: string[] = ['id', 'email', 'is_admin', 'is_approved', 'created_at', 'actions'];
  pendingDisplayedColumns: string[] = ['id', 'email', 'created_at', 'actions'];
  isLoading = signal(false);
  isPendingLoading = signal(false);
  showCreateForm = signal(false);

  createUserForm: FormGroup;

  constructor() {
    this.createUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
    });
  }

  ngOnInit() {
    this.loadUsers();
    this.loadPendingUsers();
  }

  loadUsers() {
    this.isLoading.set(true);
    const subscription = this.adminService.getAllUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load users', error);
        this.snackBar.open('Failed to load users', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  loadPendingUsers() {
    this.isPendingLoading.set(true);
    const subscription = this.adminService.getPendingUsers().subscribe({
      next: (users) => {
        this.pendingUsers.set(users);
        this.isPendingLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load pending users', error);
        this.snackBar.open('Failed to load pending users', 'Close', { duration: 3000 });
        this.isPendingLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  approveUser(userId: number, email: string) {
    const subscription = this.adminService.approveUser(userId).subscribe({
      next: (user) => {
        this.pendingUsers.update(users => users.filter(u => u.id !== userId));
        this.users.update(users => [...users, user]);
        this.snackBar.open(`User ${email} approved successfully`, 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to approve user', error);
        const errorMessage = error.error?.detail || 'Failed to approve user';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  rejectUser(userId: number, email: string) {
    if (confirm(`Are you sure you want to reject and delete the pending user ${email}?`)) {
      const subscription = this.adminService.rejectUser(userId).subscribe({
        next: () => {
          this.pendingUsers.update(users => users.filter(u => u.id !== userId));
          this.snackBar.open(`User ${email} rejected and deleted`, 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to reject user', error);
          const errorMessage = error.error?.detail || 'Failed to reject user';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  toggleCreateForm() {
    this.showCreateForm.set(!this.showCreateForm());
    if (!this.showCreateForm()) {
      this.createUserForm.reset();
    }
  }

  createUser() {
    if (this.createUserForm.valid) {
      const userData: UserCreate = this.createUserForm.value;
      const subscription = this.adminService.createUser(userData).subscribe({
        next: (user) => {
          this.users.update(users => [...users, user]);
          this.snackBar.open('User created successfully', 'Close', { duration: 3000 });
          this.createUserForm.reset();
          this.showCreateForm.set(false);
        },
        error: (error) => {
          console.error('Failed to create user', error);
          const errorMessage = error.error?.detail || 'Failed to create user';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  openEditDialog(user: User) {
    const dialogData: EditUserDialogData = { user };
    const dialogRef = this.dialog.open(EditUserDialog, {
      width: '500px',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result: EditUserDialogResult | undefined) => {
      if (result) {
        this.saveEdit(user.id, result);
      }
    });
  }

  private saveEdit(userId: number, data: EditUserDialogResult) {
    const subscription = this.adminService.updateUser(
      userId,
      data.email,
      data.is_admin
    ).subscribe({
      next: (updatedUser) => {
        this.users.update(users => 
          users.map(u => u.id === userId ? updatedUser : u)
        );
        this.snackBar.open('User updated successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to update user', error);
        const errorMessage = error.error?.detail || 'Failed to update user';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  deleteUser(userId: number, email: string) {
    if (confirm(`Are you sure you want to delete user ${email}?`)) {
      const subscription = this.adminService.deleteUser(userId).subscribe({
        next: () => {
          this.users.update(users => users.filter(u => u.id !== userId));
          this.snackBar.open('User deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to delete user', error);
          const errorMessage = error.error?.detail || 'Failed to delete user';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  formatDate(dateString: string | null): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }
}
