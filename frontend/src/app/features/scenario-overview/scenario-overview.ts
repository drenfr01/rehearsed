import { Component } from '@angular/core';
import { FormControl, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-scenario-overview',
  imports: [ReactiveFormsModule],
  templateUrl: './scenario-overview.html',
  styleUrl: './scenario-overview.css',
})
export class ScenarioOverview {
  private scenarioOverviewValue = `You are an 8th grade mathematics teacher in the middle of a Systems of Linear Equations unit.
    You gave the following task to your students:
    Consider the equation y = 2/5 x + 1 . Write a second linear equation to create a system of linear equations with only one solution.
    You wrote the following learning objectives for your students to meet after engaging with and discussing this task:
    Students will create a system of linear equations with one solution by identifying a line with a different slope than the original line.
    Students will describe why two linear equations must have different slopes to make a system with exactly one solution.
    You are about to facilitate a full group discussion about this task. Your goal is to sequence students' ideas and thinking by using mathematical questions to guide students to meet these learning objectives.
    You have decided to use the following student work to do this.`;

  form = new FormGroup({
    scenarioId: new FormControl('', [Validators.required]),
    scenarioName: new FormControl('', [Validators.required]),
    scenarioDescription: new FormControl('', [Validators.required]),
    initialPrompt: new FormControl(this.scenarioOverviewValue, [Validators.required]),
  });

  onSubmit() {
    console.log(this.form.value);
  }
}
