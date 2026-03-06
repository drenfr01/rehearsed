import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { OneOnOneFeedbackDialog, OneOnOneFeedbackDialogData } from './one-on-one-feedback-dialog';
import { pdfDeps } from '../../core/utils/pdf-download.util';

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

  it('should set feedbackData from dialog data', () => {
    expect(component['feedbackData']).toBe('Great session!');
  });

  describe('onNewSession', () => {
    it('should close dialog and navigate to one-on-one setup', () => {
      component.onNewSession();
      expect(dialogRefSpy.close).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/app/one-on-one-setup']);
    });
  });

  describe('onReturnHome', () => {
    it('should close dialog and navigate to app root', () => {
      component.onReturnHome();
      expect(dialogRefSpy.close).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/app']);
    });
  });

  describe('onDownloadSession', () => {
    it('should generate and save a PDF from feedbackData', () => {
      const mockPdf = jasmine.createSpyObj(
        'jsPDF',
        ['setFont', 'setFontSize', 'text', 'splitTextToSize', 'addPage', 'save'],
        { internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } } },
      );
      mockPdf.splitTextToSize.and.callFake((t: string) => [t]);
      spyOn(pdfDeps, 'createPdf').and.returnValue(mockPdf);

      component.onDownloadSession();
      expect(mockPdf.save).toHaveBeenCalledWith('session-feedback.pdf');
    });
  });

  describe('template', () => {
    it('should render the Download Session button', () => {
      const buttons = fixture.nativeElement.querySelectorAll('button.action-button');
      const downloadButton = Array.from(buttons).find(
        (btn: any) => btn.textContent?.includes('Download Session'),
      );
      expect(downloadButton).toBeTruthy();
    });

    it('should render the New Session button', () => {
      const buttons = fixture.nativeElement.querySelectorAll('button.action-button');
      const newSessionButton = Array.from(buttons).find(
        (btn: any) => btn.textContent?.includes('New Session'),
      );
      expect(newSessionButton).toBeTruthy();
    });

    it('should render the Return to Home Page button', () => {
      const buttons = fixture.nativeElement.querySelectorAll('button.action-button');
      const homeButton = Array.from(buttons).find(
        (btn: any) => btn.textContent?.includes('Return to Home Page'),
      );
      expect(homeButton).toBeTruthy();
    });

    it('should render app-scenario-feedback component', () => {
      const feedbackEl = fixture.nativeElement.querySelector('app-scenario-feedback');
      expect(feedbackEl).toBeTruthy();
    });
  });
});
