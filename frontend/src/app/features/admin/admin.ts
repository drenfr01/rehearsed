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
  displayedColumns: string[] = ['id', 'email', 'is_admin', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);

  createUserForm: FormGroup;
  editingUser = signal<User | null>(null);
  editUserForm: FormGroup;

  constructor() {
    this.createUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
    });

    this.editUserForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      is_admin: [false],
    });
  }

  ngOnInit() {
    this.loadUsers();
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

  startEdit(user: User) {
    this.editingUser.set(user);
    this.editUserForm.patchValue({
      email: user.email,
      is_admin: user.is_admin,
    });
  }

  cancelEdit() {
    this.editingUser.set(null);
    this.editUserForm.reset();
  }

  saveEdit(userId: number) {
    if (this.editUserForm.valid) {
      const formValue = this.editUserForm.value;
      const subscription = this.adminService.updateUser(
        userId,
        formValue.email,
        formValue.is_admin
      ).subscribe({
        next: (updatedUser) => {
          this.users.update(users => 
            users.map(u => u.id === userId ? updatedUser : u)
          );
          this.snackBar.open('User updated successfully', 'Close', { duration: 3000 });
          this.cancelEdit();
        },
        error: (error) => {
          console.error('Failed to update user', error);
          const errorMessage = error.error?.detail || 'Failed to update user';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
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

