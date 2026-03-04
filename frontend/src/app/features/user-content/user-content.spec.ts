import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { UserContent } from './user-content';

describe('UserContent', () => {
  let component: UserContent;
  let fixture: ComponentFixture<UserContent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserContent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(UserContent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
