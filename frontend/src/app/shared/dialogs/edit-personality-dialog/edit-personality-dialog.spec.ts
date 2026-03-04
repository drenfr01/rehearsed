import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { EditPersonalityDialog, EditPersonalityDialogData } from './edit-personality-dialog';

describe('EditPersonalityDialog', () => {
  let component: EditPersonalityDialog;
  let fixture: ComponentFixture<EditPersonalityDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<EditPersonalityDialog>>;

  const mockData: EditPersonalityDialogData = {
    personality: {
      id: 1, name: 'Curious', personality_description: 'Always asking questions',
    },
  };

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [EditPersonalityDialog],
      providers: [
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EditPersonalityDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with personality data', () => {
    expect(component.editForm.value.name).toBe('Curious');
    expect(component.editForm.value.personality_description).toBe('Always asking questions');
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
      expect(dialogRefSpy.close).toHaveBeenCalledWith({
        name: 'Curious',
        personality_description: 'Always asking questions',
      });
    });

    it('should not close when name is too short', () => {
      component.editForm.controls['name'].setValue('A');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });

    it('should not close when description is too short', () => {
      component.editForm.controls['personality_description'].setValue('short');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });
  });
});
