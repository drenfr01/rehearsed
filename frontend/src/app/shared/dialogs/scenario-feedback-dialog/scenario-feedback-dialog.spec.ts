import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { MatDialogRef } from '@angular/material/dialog';
import { ScenarioFeedbackDialog } from './scenario-feedback-dialog';
import { ChatGraphService } from '../../../core/services/chat-graph.service';
import { pdfDeps } from '../../../core/utils/pdf-download.util';

describe('ScenarioFeedbackDialog', () => {
  let component: ScenarioFeedbackDialog;
  let fixture: ComponentFixture<ScenarioFeedbackDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<ScenarioFeedbackDialog>>;
  let router: Router;
  let chatGraphService: ChatGraphService;

  beforeEach(async () => {
    localStorage.clear();
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [ScenarioFeedbackDialog],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: MatDialogRef, useValue: dialogRefSpy },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    chatGraphService = TestBed.inject(ChatGraphService);
    spyOn(router, 'navigate');
    spyOn(chatGraphService, 'resetGraphMessages');

    fixture = TestBed.createComponent(ScenarioFeedbackDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have feedbackData default to null', () => {
    expect(component['feedbackData']).toBeNull();
  });

  describe('onNewSession', () => {
    it('should reset messages, close dialog, and navigate to scenario selection', () => {
      component.onNewSession();
      expect(chatGraphService.resetGraphMessages).toHaveBeenCalled();
      expect(dialogRefSpy.close).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/app/scenario-selection']);
    });
  });

  describe('onReturnHome', () => {
    it('should reset messages, close dialog, and navigate to home', () => {
      component.onReturnHome();
      expect(chatGraphService.resetGraphMessages).toHaveBeenCalled();
      expect(dialogRefSpy.close).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/app']);
    });
  });

  describe('onDownloadSession', () => {
    it('should generate and save a PDF', () => {
      const mockPdf = jasmine.createSpyObj(
        'jsPDF',
        ['setFont', 'setFontSize', 'text', 'splitTextToSize', 'addPage', 'save'],
        { internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } } },
      );
      mockPdf.splitTextToSize.and.callFake((t: string) => [t]);
      spyOn(pdfDeps, 'createPdf').and.returnValue(mockPdf);

      (component as any).feedbackData = 'Some feedback text';
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
  });
});
