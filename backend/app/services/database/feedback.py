"""Feedback database repository."""

from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select, Engine

from app.core.logging import logger
from app.models.feedback import Feedback, FeedbackType


class FeedbackRepository:
    """Repository for Feedback model database operations."""
    
    def __init__(self, engine: Engine):
        """Initialize feedback repository with database engine.
        
        Args:
            engine: The SQLModel Engine instance
        """
        self._engine = engine
    
    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        return self._engine
    
    async def get_feedback(self, feedback_id: int) -> Optional[Feedback]:
        """Get a feedback by ID.

        Args:
            feedback_id: The ID of the feedback to retrieve

        Returns:
            Optional[Feedback]: The feedback if found, None otherwise
        """
        with Session(self.engine) as session:
            statement = select(Feedback).where(Feedback.id == feedback_id)
            feedback = session.exec(statement).first()
            return feedback

    async def get_feedback_by_type(self, feedback_type: FeedbackType | str, scenario_id: int) -> Optional[Feedback]:
        """Get a feedback by type and scenario.

        Args:
            feedback_type: The type of feedback to retrieve (FeedbackType.INLINE or FeedbackType.SUMMARY)
            scenario_id: The ID of the scenario to get feedback for

        Returns:
            Optional[Feedback]: The feedback if found, None otherwise
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)
        with Session(self.engine) as session:
            statement = select(Feedback).where(
                Feedback.feedback_type == feedback_type,
                Feedback.scenario_id == scenario_id
            )
            feedback = session.exec(statement).first()
            return feedback

    async def get_all_feedback(self) -> List[Feedback]:
        """Get all feedback in the system.

        Returns:
            List[Feedback]: List of all feedback
        """
        with Session(self.engine) as session:
            statement = select(Feedback).order_by(Feedback.created_at)
            feedbacks = session.exec(statement).all()
            return feedbacks

    async def create_feedback(
        self,
        feedback_type: FeedbackType | str,
        scenario_id: int,
        objective: str,
        instructions: str,
        constraints: str,
        context: str,
        output_format: str = "",
    ) -> Feedback:
        """Create a new feedback.

        Args:
            feedback_type: Type of feedback ("inline" or "summary")
            scenario_id: The ID of the scenario this feedback belongs to
            objective: The objective of the feedback
            instructions: The instructions for the feedback
            constraints: The constraints for the feedback
            context: The context for the feedback
            output_format: The output format for the feedback

        Returns:
            Feedback: The created feedback
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        with Session(self.engine) as session:
            feedback = Feedback(
                feedback_type=feedback_type,
                scenario_id=scenario_id,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
                output_format=output_format,
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("feedback_created", feedback_id=feedback.id, feedback_type=feedback_type.value, scenario_id=scenario_id)
            return feedback

    async def update_feedback(
        self,
        feedback_id: int,
        feedback_type: Optional[FeedbackType | str] = None,
        scenario_id: Optional[int] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Feedback:
        """Update a feedback's attributes.

        Args:
            feedback_id: The ID of the feedback to update
            feedback_type: Optional new feedback type
            scenario_id: Optional new scenario ID
            objective: Optional new objective
            instructions: Optional new instructions
            constraints: Optional new constraints
            context: Optional new context
            output_format: Optional new output format

        Returns:
            Feedback: The updated feedback

        Raises:
            HTTPException: If feedback is not found
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                raise HTTPException(status_code=404, detail="Feedback not found")

            if feedback_type is not None:
                if isinstance(feedback_type, str):
                    feedback_type = FeedbackType(feedback_type)
                feedback.feedback_type = feedback_type
            if scenario_id is not None:
                feedback.scenario_id = scenario_id
            if objective is not None:
                feedback.objective = objective
            if instructions is not None:
                feedback.instructions = instructions
            if constraints is not None:
                feedback.constraints = constraints
            if context is not None:
                feedback.context = context
            if output_format is not None:
                feedback.output_format = output_format

            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("feedback_updated", feedback_id=feedback_id)
            return feedback

    async def delete_feedback(self, feedback_id: int) -> bool:
        """Delete a feedback by ID.

        Args:
            feedback_id: The ID of the feedback to delete

        Returns:
            bool: True if deletion was successful, False if feedback not found
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                return False

            session.delete(feedback)
            session.commit()
            logger.info("feedback_deleted", feedback_id=feedback_id)
            return True

    async def get_feedback_for_user(self, user_id: int) -> List[Feedback]:
        """Get all feedback available to a user (global + user's local).

        Args:
            user_id: The ID of the user

        Returns:
            List[Feedback]: List of global and user's local feedback
        """
        with Session(self.engine) as session:
            statement = select(Feedback).where(
                or_(Feedback.owner_id.is_(None), Feedback.owner_id == user_id)
            ).order_by(Feedback.created_at)
            feedbacks = session.exec(statement).all()
            return list(feedbacks)

    async def get_user_local_feedback(self, user_id: int) -> List[Feedback]:
        """Get only user's local feedback (not global).

        Args:
            user_id: The ID of the user

        Returns:
            List[Feedback]: List of user's local feedback only
        """
        with Session(self.engine) as session:
            statement = select(Feedback).where(
                Feedback.owner_id == user_id
            ).order_by(Feedback.created_at)
            feedbacks = session.exec(statement).all()
            return list(feedbacks)

    async def copy_feedback_to_user(self, feedback_id: int, user_id: int) -> Feedback:
        """Copy a global feedback to a user's local feedback.

        Args:
            feedback_id: The ID of the feedback to copy
            user_id: The ID of the user to copy to

        Returns:
            Feedback: The new local copy of the feedback

        Raises:
            HTTPException: If feedback is not found
        """
        with Session(self.engine) as session:
            original = session.get(Feedback, feedback_id)
            if not original:
                raise HTTPException(status_code=404, detail="Feedback not found")

            new_feedback = Feedback(
                feedback_type=original.feedback_type,
                scenario_id=original.scenario_id,
                objective=original.objective,
                instructions=original.instructions,
                constraints=original.constraints,
                context=original.context,
                output_format=original.output_format,
                owner_id=user_id,
            )
            session.add(new_feedback)
            session.commit()
            session.refresh(new_feedback)

            logger.info("feedback_copied_to_user", 
                       original_id=feedback_id, 
                       new_id=new_feedback.id, 
                       user_id=user_id)
            return new_feedback

    async def create_user_feedback(
        self,
        user_id: int,
        feedback_type: FeedbackType | str,
        scenario_id: int,
        objective: str,
        instructions: str,
        constraints: str,
        context: str,
        output_format: str = "",
    ) -> Feedback:
        """Create a new user-local feedback.

        Args:
            user_id: The owner user's ID
            feedback_type: Type of feedback
            scenario_id: The ID of the scenario this feedback belongs to
            objective: The objective
            instructions: The instructions
            constraints: The constraints
            context: The context
            output_format: The output format

        Returns:
            Feedback: The created feedback
        """
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        with Session(self.engine) as session:
            feedback = Feedback(
                feedback_type=feedback_type,
                scenario_id=scenario_id,
                objective=objective,
                instructions=instructions,
                constraints=constraints,
                context=context,
                output_format=output_format,
                owner_id=user_id,
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("user_feedback_created", feedback_id=feedback.id, user_id=user_id, scenario_id=scenario_id)
            return feedback

    async def update_user_feedback(
        self,
        feedback_id: int,
        user_id: int,
        feedback_type: Optional[FeedbackType | str] = None,
        scenario_id: Optional[int] = None,
        objective: Optional[str] = None,
        instructions: Optional[str] = None,
        constraints: Optional[str] = None,
        context: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Feedback:
        """Update a user's local feedback (with ownership check).

        Args:
            feedback_id: The ID of the feedback to update.
            user_id: The ID of the user (for ownership verification).
            feedback_type: Optional new feedback type.
            scenario_id: Optional new scenario ID.
            objective: Optional new objective.
            instructions: Optional new instructions.
            constraints: Optional new constraints.
            context: Optional new context.
            output_format: Optional new output format.

        Returns:
            Feedback: The updated feedback.

        Raises:
            HTTPException: If feedback is not found or user doesn't own it.
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                raise HTTPException(status_code=404, detail="Feedback not found")
            if feedback.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to edit this feedback")

            if feedback_type is not None:
                if isinstance(feedback_type, str):
                    feedback_type = FeedbackType(feedback_type)
                feedback.feedback_type = feedback_type
            if scenario_id is not None:
                feedback.scenario_id = scenario_id
            if objective is not None:
                feedback.objective = objective
            if instructions is not None:
                feedback.instructions = instructions
            if constraints is not None:
                feedback.constraints = constraints
            if context is not None:
                feedback.context = context
            if output_format is not None:
                feedback.output_format = output_format

            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            logger.info("user_feedback_updated", feedback_id=feedback_id, user_id=user_id)
            return feedback

    async def delete_user_feedback(self, feedback_id: int, user_id: int) -> bool:
        """Delete a user's local feedback (with ownership check).

        Args:
            feedback_id: The ID of the feedback to delete
            user_id: The ID of the user (for ownership verification)

        Returns:
            bool: True if deletion was successful

        Raises:
            HTTPException: If feedback is not found or user doesn't own it
        """
        with Session(self.engine) as session:
            feedback = session.get(Feedback, feedback_id)
            if not feedback:
                raise HTTPException(status_code=404, detail="Feedback not found")
            if feedback.owner_id != user_id:
                raise HTTPException(status_code=403, detail="You don't have permission to delete this feedback")

            session.delete(feedback)
            session.commit()
            logger.info("user_feedback_deleted", feedback_id=feedback_id, user_id=user_id)
            return True
