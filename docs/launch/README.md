# Launch kit

Everything needed to make the repo findable and fundable. Steps marked **owner** need the `Noam-Marom`
account (repo admin, money, or posting as yourself); the rest is already in the repo.

## 1. Repository settings (owner, 3 minutes)

Repo page → the ⚙ next to **About**:

- **Description:** `Claude skills for university students in any degree: assignment coach, grade estimate, academic writing, exam prep, lecture notes, study planner, Moodle sync. English + Hebrew (RTL).`
- **Website:** `https://github.com/Noam-Marom/academic-students#install`
- **Topics:** `claude` `claude-code` `claude-skills` `claude-plugin` `anthropic` `ai-for-education` `students`
  `university` `academic-writing` `study-tools` `exam-prep` `moodle` `mcp` `prompt-injection` `rtl` `hebrew`
  `edtech` `agent-skills`

Settings → General:

- **Social preview** → upload `docs/images/social-preview.png` (this is the card shown on WhatsApp, LinkedIn,
  X and Slack when the link is shared).
- **Features** → tick **Discussions** (questions go there instead of issues) and **Sponsorships** (after step 3).

Settings → Branches → **Add rule** for `main`: *Require a pull request before merging* + *Require review from
Code Owners*. `.github/CODEOWNERS` already names you, so nobody's change reaches the users without your
approval. (Claude pushes to `main` directly today; with the rule on, it opens pull requests instead.)

## 2. Releases (owner, 1 minute)

Releases → **Draft a new release** → tag `v0.2.1` on `main` → **Publish**. The release workflow attaches the
plugin zip and one zip per skill; `INSTALL.md` links to them.

## 3. GitHub Sponsors (owner)

1. https://github.com/sponsors → **Get started** → join as an individual. GitHub asks for a bank account
   (or Stripe Connect), tax details and two-factor authentication; approval usually takes a few days.
   Do this part yourself; nobody else should type those details.
2. Paste the profile below, add the tiers, publish.
3. `.github/FUNDING.yml` is already in the repo, so the **♥ Sponsor** button appears on the repo as soon as
   the profile is live. The READMEs already link to `github.com/sponsors/Noam-Marom`.

### Profile text (paste into "Introduction")

> **Support academic-students — free Claude skills for university students**
>
> academic-students is a free, open-source Claude plugin that removes the friction around studying in any
> degree: it breaks down assignments, estimates the grade an expert professor would give against the
> instructions, gives real feedback on academic writing without inventing sources, turns past exams into
> practice, summarises lectures, plans the week around real deadlines, and pulls course material from Moodle
> read-only. Every course file is scanned for hidden "AI traps" first. It never does the studying behind the
> course's back.
>
> **What sponsorship pays for**
> - 🧪 Model runs that test every skill before each release (a full run of the behaviour tests costs about $20)
> - 🌍 More languages: Arabic and Persian right-to-left support, more grading systems
> - 🎓 Discipline packs for more degrees (law, nursing, architecture, …) reviewed by students in those fields
> - 🔌 Moodle on more universities, and other learning systems (Canvas, Blackboard)
> - 🐛 Fast fixes when a skill misbehaves
>
> If academic-students saved you an evening, consider a small monthly sponsorship. Thank you ❤️

### Goal (optional)

`$100 per month` — "Monthly test runs of every skill before each release, plus a reviewer for each new
language."

### Tiers

| Monthly | Name | What the sponsor gets |
|---|---|---|
| $3 | ☕ Coffee | Sponsor badge, and my thanks |
| $5 | 📚 Student | Name in the README's Sponsors list |
| $15 | 🎓 Graduate | Name in the README + your vote on the next skill |
| $50 | 🏛️ Student union / course | Logo in the README + a discipline pack for your degree prioritised |
| One-time, any amount | ❤️ | Sponsor badge |

## 4. Getting found

Google ranks a page by how many other pages link to it and how well its words match the search. Nobody can
promise the first result for a broad search like "academic skills" (big sites and Anthropic's own pages
compete for it), but these steps give the repo its best chance, and specific searches ("claude skills for
students", "claude assignment grader", "claude hebrew rtl") are winnable:

- The README title and first line now carry the words people search: *Claude skills for university students*.
- Topics and description from step 1 (GitHub search and Google both read them).
- Links from other sites are what move rankings. In order of value:
  1. **Anthropic's plugin directory:** claude.ai → Customize → Plugins → *Submit to the directory* (the link
     shown at the bottom of the Plugins page). Being listed there is the strongest signal and puts it inside
     Claude for every user.
  2. **Awesome lists** on GitHub (search GitHub for `awesome claude skills`, `awesome-claude-code`): open a
     pull request adding one line under Education.
  3. **A post with a demo** (the before/after images, a 30-second screen recording of `/assignment-judge`):
     r/ClaudeAI, r/ClaudeCode, r/college or r/GradSchool (read each subreddit's self-promotion rule first),
     Hacker News "Show HN: Claude skills for university students", LinkedIn, X.
  4. **Israel:** Facebook and WhatsApp groups of your faculty and other universities' student unions, the
     BGU student union, Geektime / Calcalist Tech (a short pitch email: "a BGU student built…").
- Every post links to the repo, not to a zip, so stars and links all point to one URL.

### Ready to paste

**English (Reddit / Show HN):**

> I'm a third-year software engineering student and I built academic-students, a free, open-source Claude
> plugin for university students in any degree. It breaks down assignments (and splits group work), estimates
> the grade a professor would give against the instructions, gives feedback on academic writing without
> inventing sources, turns past exams into practice and a mock exam, summarises lectures, plans your week,
> and pulls course material from Moodle read-only. It scans every course file for hidden "if you are an AI…"
> traps first, and it never does the studying behind your course's back. Works in claude.ai, the desktop app
> and Claude Code. Feedback welcome: https://github.com/Noam-Marom/academic-students

**Hebrew (WhatsApp / Facebook):**

> בניתי פלאגין חינמי וקוד פתוח ל-Claude לסטודנטים בכל תואר: הוא מפרק מטלות ומחלק עבודה בקבוצה, מעריך כמה
> המטלה הייתה מקבלת אצל המרצה לפי ההוראות, נותן משוב על עבודות בלי להמציא מקורות, הופך מבחנים קודמים לתרגול,
> מסכם הרצאות, מתכנן את השבוע ומוריד חומרים מהמודל (קריאה בלבד). הוא גם סורק כל קובץ אחרי "מלכודות AI"
> נסתרות, וכותב עברית עם מונחים באנגלית בלי שהשורות יתהפכו. ההתקנה לוקחת דקה:
> https://github.com/Noam-Marom/academic-students
> אשמח לכוכב ⭐ ולפידבק!
