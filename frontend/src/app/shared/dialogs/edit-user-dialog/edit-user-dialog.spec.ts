import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { EditUserDialog, EditUserDialogData } from './edit-user-dialog';

describe('EditUserDialog', () => {
  let component: EditUserDialog;
  let fixture: ComponentFixture<EditUserDialog>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<EditUserDialog>>;

  const mockData: EditUserDialogData = {
    user: {
      id: 1, email: 'user@test.com', is_admin: false, is_approved: true, created_at: '2025-01-01',
    },
  };

  beforeEach(async () => {
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [EditUserDialog],
      providers: [
        provideAnimations(),
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(EditUserDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize form with user data', () => {
    expect(component.editForm.value.email).toBe('user@test.com');
    expect(component.editForm.value.is_admin).toBe(false);
  });

  it('should expose dialog data', () => {
    expect(component.data.user.id).toBe(1);
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
      expect(dialogRefSpy.close).toHaveBeenCalledWith({ email: 'user@test.com', is_admin: false });
    });

    it('should not close when email is invalid', () => {
      component.editForm.controls['email'].setValue('not-an-email');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });

    it('should not close when email is empty', () => {
      component.editForm.controls['email'].setValue('');
      component.onSave();
      expect(dialogRefSpy.close).not.toHaveBeenCalled();
    });

    it('should allow toggling admin status', () => {
      component.editForm.controls['is_admin'].setValue(true);
      component.onSave();
      expect(dialogRefSpy.close).toHaveBeenCalledWith(jasmine.objectContaining({ is_admin: true }));
    });
  });
});
