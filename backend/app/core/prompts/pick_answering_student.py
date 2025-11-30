PICK_ANSWERING_STUDENT_SYSTEM_INSTRUCTIONS = """
If the prior user message specifies a student name, pick the number that corresponds to the student name.

If the prior user asks for a different student to respond, pick the number that corresponds to a student that has not yet responded.

Otherwise based on the user message and these student profiles, pick which student in the integer range of 1 to {student_number_range} should respond:

{messages}
{student_profiles}

"""