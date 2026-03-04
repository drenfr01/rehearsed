import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { OneOnOneFeedbackDialog, OneOnOneFeedbackDialogData } from './one-on-one-feedback-dialog';

describe('OneOnOneFeedbackDialog', () => {
  let component: OneOnOneFeedbackDialog;
  let fixture: ComponentFixture<OneOnOneFeedbackDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<OneOnOneFeedbackDialog>>;
  let router: Router;

  const mockData: OneOnOneFeedbackDialogData = {
    feedback: 'Great session!',
  };

  beforeEach(async () => {
    localStorage.clear();
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [OneOnOneFeedbackDialog],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    spyOn(router, 'navigate');

    fixture = TestBed.createComponent(OneOnOneFeedbackDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('onNewSession should close dialog and navigate to setup', () => {
    component.onNewSession();
    expect(dialogRefSpy.close).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/app/one-on-one-setup']);
  });

  it('onReturnHome should close dialog and navigate to app root', () => {
    component.onReturnHome();
    expect(dialogRefSpy.close).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/app']);
  });
});
