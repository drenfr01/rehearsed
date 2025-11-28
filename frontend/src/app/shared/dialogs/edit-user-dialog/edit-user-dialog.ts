import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { User } from '../../../core/models/user.model';

export interface EditUserDialogData {
  user: User;
}

export interface EditUserDialogResult {
  email: string;
  is_admin: boolean;
}

@Component({
  selector: 'app-edit-user-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSlideToggleModule,
  ],
  templateUrl: './edit-user-dialog.html',
})
export class EditUserDialog {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<EditUserDialog>);
  public data: EditUserDialogData = inject(MAT_DIALOG_DATA);

  editForm: FormGroup;

  constructor() {
    this.editForm = this.fb.group({
      email: [this.data.user.email, [Validators.required, Validators.email]],
      is_admin: [this.data.user.is_admin],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editForm.valid) {
      const result: EditUserDialogResult = this.editForm.value;
      this.dialogRef.close(result);
    }
  }
}

