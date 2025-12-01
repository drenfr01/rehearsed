PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS = """
You must select which student should respond to the teacher's latest message.

<STUDENT_PROFILES>
{student_profiles}
</STUDENT_PROFILES>

<CONVERSATION_HISTORY>
{messages}
</CONVERSATION_HISTORY>

<INSTRUCTIONS>
1. Look at the conversation history. AI messages prefixed with [StudentName] indicate which student spoke.
2. If the teacher specifies a student by name, pick that student's number.
3. If the teacher asks for a different student, someone else, or "anyone else" to respond, pick a student who has NOT yet spoken in the recent conversation.
4. If the teacher asks a follow-up question about a specific student's answer, pick that student.
5. Otherwise, pick the most appropriate student based on the question and their profile.

Pick a student number in the range 1 to {student_number_range}.
</INSTRUCTIONS>
"""