import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { MatDialogRef } from '@angular/material/dialog';
import { ScenarioFeedbackDialog } from './scenario-feedback-dialog';
import { ChatGraphService } from '../../../core/services/chat-graph.service';

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
    it('should not throw', () => {
      expect(() => component.onDownloadSession()).not.toThrow();
    });
  });
});
