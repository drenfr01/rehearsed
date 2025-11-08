import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ScenarioSelection } from './scenario-selection';

describe('ScenarioSelection', () => {
  let component: ScenarioSelection;
  let fixture: ComponentFixture<ScenarioSelection>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScenarioSelection]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ScenarioSelection);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
