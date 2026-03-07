import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { EditAgentDialog, EditAgentDialogData } from './edit-agent-dialog';

describe('EditAgentDialog', () => {
  let component: EditAgentDialog;
  let fixture: ComponentFixture<EditAgentDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<EditAgentDialog>>;

  const mockData: EditAgentDialogData = {
    agent: {
      id: 'a1', name: 'Alice', scenario_id: 1, agent_personality_id: 2,
      voice: 'Kore', display_text_color: 'teal', objective: 'teach',
      instructions: 'inst', constraints: 'con', context: 'ctx',
    },
    scenarios: [{ id: 1, name: 'S1', description: 'd', overview: 'o', system_instructions: 'si', initial_prompt: 'ip', teaching_objectives: 'to' }],
    personalities: [{ id: 2, name: 'Curious', personality_description: 'desc' }],
    voices: [{ id: 1, voice_name: 'Kore' }],
    avatars: [{ id: 1, name: 'Ash', file_path: 'Ash.jpg' }, { id: 2, name: 'Sage', file_path: 'Sage.jpg' }],
  };

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [EditAgentDialog],
      providers: [
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EditAgentDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with agent data', () => {
    expect(component.editForm.value.name).toBe('Alice');
    expect(component.editForm.value.scenario_id).toBe(1);
    expect(component.editForm.value.agent_personality_id).toBe(2);
    expect(component.editForm.value.voice).toBe('Kore');
    expect(component.editForm.value.avatar_gcs_uri).toBe('');
  });

  it('should expose dialog data', () => {
    expect(component.data.scenarios.length).toBe(1);
    expect(component.data.personalities.length).toBe(1);
    expect(component.data.voices.length).toBe(1);
    expect(component.data.avatars!.length).toBe(2);
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
      expect(dialogRefSpy.close).toHaveBeenCalledWith(jasmine.objectContaining({ name: 'Alice' }));
    });

    it('should not close dialog when form is invalid', () => {
      component.editForm.controls['name'].setValue('');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });
  });
});
