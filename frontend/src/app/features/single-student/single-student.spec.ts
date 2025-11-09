import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SingleStudent } from './single-student';

describe('SingleStudent', () => {
  let component: SingleStudent;
  let fixture: ComponentFixture<SingleStudent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SingleStudent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SingleStudent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
