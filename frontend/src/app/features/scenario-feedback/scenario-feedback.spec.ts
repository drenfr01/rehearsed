import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScenarioFeedback } from './scenario-feedback';

describe('ScenarioFeedback', () => {
  let component: ScenarioFeedback;
  let fixture: ComponentFixture<ScenarioFeedback>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScenarioFeedback]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScenarioFeedback);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
