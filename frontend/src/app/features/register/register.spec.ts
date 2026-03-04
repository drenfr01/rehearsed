import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Register } from './register.component';

describe('Register', () => {
  let component: Register;
  let fixture: ComponentFixture<Register>;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Register],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Register);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have email, password, and confirmPassword controls', () => {
    expect(component.form.controls['email']).toBeTruthy();
    expect(component.form.controls['password']).toBeTruthy();
    expect(component.form.controls['confirmPassword']).toBeTruthy();
  });

  it('should be invalid by default', () => {
    expect(component.form.valid).toBeFalse();
  });

  describe('password validation', () => {
    it('hasMinLength should return false for short passwords', () => {
      component.form.controls['password'].setValue('Ab1!');
      expect(component.hasMinLength()).toBeFalse();
    });

    it('hasMinLength should return true for 8+ char passwords', () => {
      component.form.controls['password'].setValue('Abcdefg1!');
      expect(component.hasMinLength()).toBeTrue();
    });

    it('hasUppercase should detect uppercase letters', () => {
      component.form.controls['password'].setValue('abcdefg');
      expect(component.hasUppercase()).toBeFalse();
      component.form.controls['password'].setValue('Abcdefg');
      expect(component.hasUppercase()).toBeTrue();
    });

    it('hasLowercase should detect lowercase letters', () => {
      component.form.controls['password'].setValue('ABCDEFG');
      expect(component.hasLowercase()).toBeFalse();
      component.form.controls['password'].setValue('ABCDEFg');
      expect(component.hasLowercase()).toBeTrue();
    });

    it('hasNumber should detect numbers', () => {
      component.form.controls['password'].setValue('Abcdefg!');
      expect(component.hasNumber()).toBeFalse();
      component.form.controls['password'].setValue('Abcdefg1!');
      expect(component.hasNumber()).toBeTrue();
    });

    it('hasSpecialChar should detect special characters', () => {
      component.form.controls['password'].setValue('Abcdefg1');
      expect(component.hasSpecialChar()).toBeFalse();
      component.form.controls['password'].setValue('Abcdefg1!');
      expect(component.hasSpecialChar()).toBeTrue();
    });
  });

  describe('passwordsMatch', () => {
    it('should return false when passwords differ', () => {
      component.form.controls['password'].setValue('Password1!');
      component.form.controls['confirmPassword'].setValue('Different1!');
      expect(component.passwordsMatch).toBeFalse();
    });

    it('should return true when passwords match', () => {
      component.form.controls['password'].setValue('Password1!');
      component.form.controls['confirmPassword'].setValue('Password1!');
      expect(component.passwordsMatch).toBeTrue();
    });
  });
});
