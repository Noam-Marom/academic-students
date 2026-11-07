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
  consent. Recording laws differ: some countries let a participant record, others need everyone's
  consent, and most universities restrict recording lectures regardless. Rights in the lecture usually belong
  to the lecturer or the university. When the student says the recording was made without permission, say once, in one sentence,
  that the course's rules may not allow it and that a published recording or the slides are the safe source;
  then offer to work from the slides or the student's own notes. Do not lecture and do not repeat it.
- Anything with other students' voices that the student intends to share: the summary is for the student.

## What the skill always does

- Runs `faster-whisper` on the student's machine only (`scripts/transcribe.py`); if it is not installed, the
  student exports a transcript (Zoom, YouTube, Panopto, Teams) and the skill converts the `.vtt`/`.srt` locally.
- Never sends audio to any service. The transcript, like any file the assistant reads, is processed by your AI provider.
- Keeps transcripts and summaries in the course folder or the scratch directory; never deletes the recording.
- Does not put names of students who spoke in the recording into the summary ("a student asked…").
