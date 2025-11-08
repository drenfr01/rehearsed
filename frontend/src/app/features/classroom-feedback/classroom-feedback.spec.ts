import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ClassroomFeedback } from './classroom-feedback';

describe('ClassroomFeedback', () => {
  let component: ClassroomFeedback;
  let fixture: ComponentFixture<ClassroomFeedback>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClassroomFeedback]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ClassroomFeedback);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
