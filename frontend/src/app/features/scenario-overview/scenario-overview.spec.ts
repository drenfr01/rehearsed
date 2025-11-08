import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScenarioOverview } from './scenario-overview';

describe('ScenarioOverview', () => {
  let component: ScenarioOverview;
  let fixture: ComponentFixture<ScenarioOverview>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScenarioOverview]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScenarioOverview);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
