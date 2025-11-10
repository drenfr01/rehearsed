import { TestBed } from '@angular/core/testing';

import { Scenario } from './scenario.service';

describe('Scenario', () => {
  let service: Scenario;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Scenario);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
