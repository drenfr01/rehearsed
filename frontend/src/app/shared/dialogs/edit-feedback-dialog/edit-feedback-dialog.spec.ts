import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { EditFeedbackDialog, EditFeedbackDialogData } from './edit-feedback-dialog';

describe('EditFeedbackDialog', () => {
  let component: EditFeedbackDialog;
  let fixture: ComponentFixture<EditFeedbackDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<EditFeedbackDialog>>;

  const mockData: EditFeedbackDialogData = {
    feedback: {
      id: 1, feedback_type: 'inline', scenario_id: 1,
      objective: 'obj', instructions: 'inst', constraints: 'con',
      context: 'ctx', output_format: 'fmt', created_at: '2025-01-01',
    },
    scenarios: [{ id: 1, name: 'S1', description: 'd', overview: 'o', system_instructions: 'si', initial_prompt: 'ip', teaching_objectives: 'to' }],
  };

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [EditFeedbackDialog],
      providers: [
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EditFeedbackDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with feedback data', () => {
    expect(component.editForm.value.feedback_type).toBe('inline');
    expect(component.editForm.value.objective).toBe('obj');
    expect(component.editForm.value.scenario_id).toBe(1);
  });

  it('should have feedback types', () => {
    expect(component.feedbackTypes).toEqual(['inline', 'summary']);
  });

  describe('getFeedbackTypeLabel', () => {
    it('should return correct labels', () => {
      expect(component.getFeedbackTypeLabel('inline')).toBe('Inline Feedback');
      expect(component.getFeedbackTypeLabel('summary')).toBe('Summary Feedback');
    });
  });

  describe('onCancel', () => {
    it('should close dialog without result', () => {
      component.onCancel();
      expect(dialogRefSpy.close).toHaveBeenCalledWith();
    });
  });

  describe('onSave', () => {
    it('should close dialog with form value when valid', () => {
      component.onSave();
      expect(dialogRefSpy.close).toHaveBeenCalledWith(jasmine.objectContaining({ feedback_type: 'inline' }));
    });

    it('should not close when form is invalid', () => {
      component.editForm.controls['objective'].setValue('');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });
  });
});
