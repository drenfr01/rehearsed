import { Component, DestroyRef, inject, signal } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';
import { Router, RouterLink } from '@angular/router';
import { FormControl, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-register',
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    CommonModule,
    RouterLink,
  ],
  templateUrl: './register.html',
  styleUrl: './register.css',
})
export class Register {
  private router = inject(Router);
  private authService = inject(AuthService);
  protected isLoading = signal(false);
  protected success = signal(false);
  private destroyRef = inject(DestroyRef);
  protected error = signal<string>('');

  form = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
    password: new FormControl('', [
      Validators.required,
      Validators.minLength(8),
      this.passwordStrengthValidator,
    ]),
    confirmPassword: new FormControl('', [Validators.required]),
  });

  /**
   * Custom validator for password strength requirements
   */
  passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
    const password = control.value;
    if (!password) return null;

    const errors: ValidationErrors = {};

    if (!/[A-Z]/.test(password)) {
      errors['uppercase'] = 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(password)) {
      errors['lowercase'] = 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(password)) {
      errors['number'] = 'Password must contain at least one number';
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors['special'] = 'Password must contain at least one special character';
    }

    return Object.keys(errors).length > 0 ? errors : null;
  }

  /**
   * Check if passwords match
   */
  get passwordsMatch(): boolean {
    return this.form.value.password === this.form.value.confirmPassword;
  }

  /**
   * Password requirement checks for template
   */
  hasMinLength(): boolean {
    return !!this.form.value.password && this.form.value.password.length >= 8;
  }

  hasUppercase(): boolean {
    return !!this.form.value.password && /[A-Z]/.test(this.form.value.password);
  }

  hasLowercase(): boolean {
    return !!this.form.value.password && /[a-z]/.test(this.form.value.password);
  }

  hasNumber(): boolean {
    return !!this.form.value.password && /[0-9]/.test(this.form.value.password);
  }

  hasSpecialChar(): boolean {
    return !!this.form.value.password && /[!@#$%^&*(),.?":{}|<>]/.test(this.form.value.password);
  }

  onSubmit() {
    // Check if passwords match
    if (!this.passwordsMatch) {
      this.error.set('Passwords do not match');
      return;
    }

    this.isLoading.set(true);
    this.error.set('');

    const subscription = this.authService
      .register(this.form.value.email!, this.form.value.password!)
      .subscribe({
        next: () => {
          this.success.set(true);
          this.isLoading.set(false);
        },
        error: (error: Error) => {
          this.error.set(error.message || 'Registration failed. Please try again.');
          this.isLoading.set(false);
        },
      });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }
}

