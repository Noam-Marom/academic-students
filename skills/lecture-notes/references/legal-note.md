# Recordings: what the student may hold, and what this skill does with them

This skill transcribes lecture recordings **locally** and never uploads audio anywhere. That covers privacy
on the plugin's side. It does not decide whether the student may have the recording in the first place.

## Recordings that are fine to work with

- Recordings the university publishes to the course (Moodle, Panopto, the course YouTube channel, Zoom cloud
  recordings shared by the lecturer).
- Recordings the student made with the lecturer's consent (asked in class or by email; a course rule that
  allows recording counts).
- The student's own voice notes about the lecture.

## Recordings to stop on

- A recording made secretly in class, or a recording someone else made and passed on without the lecturer's
  consent. Israeli law (חוק האזנת סתר) allows a participant to record a conversation they take part in, but
  universities usually restrict recording lectures and redistributing them, and the lecture's content belongs
  to the lecturer. When the student says the recording was made without permission, say once, in one sentence,
  that the course's rules may not allow it and that a published recording or the slides are the safe source;
  then offer to work from the slides or the student's own notes. Do not lecture and do not repeat it.
- Anything with other students' voices that the student intends to share: the summary is for the student.

## What the skill always does

- Runs `faster-whisper` on the student's machine only (`scripts/transcribe.py`); if it is not installed, the
  student exports a transcript (Zoom, YouTube, Panopto, Teams) and the skill converts the `.vtt`/`.srt` locally.
- Never sends audio or the transcript to a web service, a transcription API, or another tool.
- Keeps transcripts and summaries in the course folder or the scratch directory; never deletes the recording.
- Does not put names of students who spoke in the recording into the summary ("a student asked…").
