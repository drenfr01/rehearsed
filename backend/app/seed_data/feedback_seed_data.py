"""This file contains the feedback seed data for the application."""

import os
from yaml import safe_load
from sqlmodel import Session, select
from app.services.database import database_service
from app.models.feedback import Feedback, FeedbackType


def load_feedback_data() -> list[Feedback]:
    """Load the feedback data from the file."""
    with open(os.path.join(os.path.dirname(__file__), "feedback_data.yaml"), "r") as f:
        feedback_data_yaml = safe_load(f)
    
    feedbacks = []
    for feedback_data in feedback_data_yaml:
        feedback = Feedback(
            id=feedback_data["id"],
            feedback_type=FeedbackType(feedback_data["feedback_type"]),
            objective=feedback_data["objective"],
            instructions=feedback_data["instructions"],
            constraints=feedback_data["constraints"],
            context=feedback_data["context"],
            output_format=feedback_data.get("output_format", ""),
        )
        feedbacks.append(feedback)
    
    return feedbacks


def seed_feedback_data():
    """Seed the feedback data into the database."""
    with Session(database_service.engine) as session:
        data_exists = session.exec(select(Feedback)).all()
        if data_exists:
            return
        for feedback in load_feedback_data():
            session.add(feedback)
        session.commit()

