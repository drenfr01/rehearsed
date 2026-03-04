import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { EditScenarioDialog, EditScenarioDialogData } from './edit-scenario-dialog';

describe('EditScenarioDialog', () => {
  let component: EditScenarioDialog;
  let fixture: ComponentFixture<EditScenarioDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<EditScenarioDialog>>;

  const mockData: EditScenarioDialogData = {
    scenario: {
      id: 1, name: 'Test Scenario', description: 'A test scenario description',
      overview: 'Scenario overview text', system_instructions: 'System instructions here',
      initial_prompt: 'Hello class', teaching_objectives: 'Learn testing',
    },
  };

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [EditScenarioDialog],
      providers: [
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EditScenarioDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with scenario data', () => {
    expect(component.editForm.value.name).toBe('Test Scenario');
    expect(component.editForm.value.description).toBe('A test scenario description');
    expect(component.editForm.value.overview).toBe('Scenario overview text');
    expect(component.editForm.value.initial_prompt).toBe('Hello class');
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
      expect(dialogRefSpy.close).toHaveBeenCalledWith(jasmine.objectContaining({ name: 'Test Scenario' }));
    });

    it('should not close when form is invalid', () => {
      component.editForm.controls['name'].setValue('');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });
  });
});
