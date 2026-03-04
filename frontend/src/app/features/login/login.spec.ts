import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Login } from './login.component';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have a form with email and password controls', () => {
    expect(component.form.controls['email']).toBeTruthy();
    expect(component.form.controls['password']).toBeTruthy();
  });

  it('should have an invalid form by default', () => {
    expect(component.form.valid).toBeFalse();
  });

  it('should validate email is required', () => {
    const email = component.form.controls['email'];
    expect(email.errors?.['required']).toBeTruthy();
  });

  it('should validate password minimum length', () => {
    component.form.controls['password'].setValue('short');
    expect(component.form.controls['password'].errors?.['minlength']).toBeTruthy();
  });

  it('should be valid with correct inputs', () => {
    component.form.controls['email'].setValue('user@test.com');
    component.form.controls['password'].setValue('password123');
    expect(component.form.valid).toBeTrue();
  });
});
