import { TestBed } from '@angular/core/testing';

import { Scenario } from './scenario';

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
