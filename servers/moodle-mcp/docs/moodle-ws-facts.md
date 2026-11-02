# Moodle Web Services — verified facts for a read-only student client

Verified against Moodle source branch `MOODLE_500_STABLE` (https://github.com/moodle/moodle) on
2026-11-02 unless marked **unverified**. Source paths are relative to the repo root.

## 1. Token via username/password — `login/token.php`

- URL: `{site}/login/token.php?username=U&password=P&service=moodle_mobile_app` (GET or POST; use POST).
  Username is lowercased/trimmed server-side. Source: `login/token.php`.
- `service` is the external-service shortname. The official mobile service constant is
  `MOODLE_OFFICIAL_MOBILE_SERVICE = 'moodle_mobile_app'` (`lib/moodlelib.php`).
- Success: `{"token": "<32-hex>", "privatetoken": "<64 chars>" | null}`. `privatetoken` is non-null
  only over HTTPS and for non-admins.
- Pre-check without credentials: `login/token.php?appsitecheck=1` → `{"appsitecheck":"ok"}`.
- Error (AJAX renderer, `lib/classes/output/core_renderer_ajax.php::fatal_error`):
  `{"error": "<message>", "errorcode": "invalidlogin", "stacktrace": null, "debuginfo": null, "reproductionlink": null}`.
  Other codes: `enablewsdescription` (web services off), `servicenotavailable` (service missing/disabled),
  `noguest`, `usernotconfirmed`, `passwordisexpired`, `sitemaintenance`, `restoredaccountresetpassword`.
  HTTP status is usually 200 (**unverified**). Failed attempts count toward the site's login lockout.
- Doc: https://docs.moodle.org/dev/Creating_a_web_service_client

## 2. Browser / SSO login — `admin/tool/mobile/launch.php`

- Params: `service` (required), `passport` (required; the app uses a random float), `urlscheme`
  (optional, default `moodlemobile`, must match `^[a-zA-Z][a-zA-Z0-9-\+\.]*$` — a URL is **not** allowed),
  `confirmed` (bool), `oauthsso` (OAuth2 issuer id → redirects via `auth/oauth2/login.php`).
- Gate: throws `pluginnotenabledorconfigured` unless `typeoflogin` is 2 or 3, or OAuth2 is enabled, or the
  user just logged in. Then `require_login()`, so the normal login page appears and bounces back.
- Output: redirect to `{urlscheme}://token={base64}` where the plaintext is
  `md5(wwwroot . passport) ::: token [::: privatetoken]`. With `confirmed=1` (or on iOS) Moodle renders a
  page containing the link instead of a 302 — useful for a paste-back flow on desktop.
- Client validation (official app `login-helper.ts::validateBrowserSSOLogin`): split on `:::`, compare
  `[0]` to `md5(siteUrl + passport)` (retry with http/https swapped), `[1]` = token, `[2]` = privatetoken.
- `urlscheme` is not validated against a configured value, only the regex. If the admin set
  `tool_mobile/forcedurlscheme`, it silently overrides the one you sent.
- Doc: https://docs.moodle.org/en/Moodle_app_guide_for_admins

## 3. `tool_mobile_get_public_config`

- Registered with `loginrequired => false`, `ajax => true` (`admin/tool/mobile/db/services.php`). Call
  without a token via `{site}/lib/ajax/service.php` POST body
  `[{"index":0,"methodname":"tool_mobile_get_public_config","args":{}}]` (**exact ajax form unverified**),
  or via REST with any valid token.
- Fields (`admin/tool/mobile/classes/api.php::get_public_config`): `typeoflogin` (1 = username/password in
  app, 2 = browser window, 3 = embedded browser), `launchurl`, `enablewebservices`, `enablemobilewebservice`,
  `maintenanceenabled`, `authnoneenabled`, `guestlogin`, `identityproviders[] = {name, iconurl, url}`,
  `wwwroot`, `sitename`, `showloginform`, `tool_mobile_disabledfeatures`, `warnings`.
- Decision: `typeoflogin == 1` → `login/token.php`; 2/3 or `identityproviders` present → launch flow.

## 4. REST call shape

- `{site}/webservice/rest/server.php?wstoken=T&wsfunction=F&moodlewsrestformat=json`; GET and POST params
  are merged. Without `moodlewsrestformat` the response is XML.
- Arrays use PHP query syntax: `courseids[0]=12&courseids[1]=13`;
  structs: `options[0][name]=excludecontents&options[0][value]=1`.
- Error JSON: `{"exception": "<class>", "errorcode": "<code>", "message": "<text>", "debuginfo": "…"}`
  with HTTP 200. If the REST protocol is disabled: HTTP 403 with no JSON.

## 5. Functions (all in the mobile service by default)

| Function | Params | Key response fields |
|---|---|---|
| `core_webservice_get_site_info` | — | `sitename, username, fullname, userid, siteurl, release, version, downloadfiles, uploadfiles, functions[]` |
| `core_enrol_get_users_courses` | `userid`, `returnusercount?` | `[{id, shortname, fullname, displayname, category, startdate, enddate, lastaccess, hidden, visible}]` |
| `core_course_get_contents` | `courseid`, `options[]` (`excludemodules, excludecontents, includestealthmodules, sectionid, sectionnumber, cmid, modname, modid`) | sections `[{id,name,visible,summary,section, modules[{id,url,name,instance,modname,description,visible, contents[{type,filename,filepath,filesize,fileurl,timemodified,mimetype}], contentsinfo}]}]` |
| `mod_assign_get_assignments` | `courseids[]?`, `capabilities[]?`, `includenotenrolledcourses?` | `courses[{id,fullname,shortname, assignments[{id,cmid,course,name,duedate,allowsubmissionsfromdate,cutoffdate,intro,introfiles,introattachments}]}]` |
| `core_calendar_get_action_events_by_timesort` | `timesortfrom=0`, `timesortto`, `aftereventid=0`, `limitnum=20` | `{events[{id,name,description,eventtype,timestart,timeduration,timesort,modulename,instance,course{...},action{name,url,actionable},url}], firstid, lastid}` |
| `core_calendar_get_calendar_upcoming_view` | `courseid=SITEID`, `categoryid` | `{events[...]}` |
| `core_calendar_get_calendar_export_token` | — (Moodle ≥ 3.10) | `{token, warnings}` for `calendar/export_execute.php` |
| `gradereport_user_get_grade_items` | `courseid`, `userid=0`, `groupid=0` | `usergrades[{courseid, userid, gradeitems[{id,itemname,itemtype,itemmodule,cmid,graderaw,gradeformatted,grademin,grademax,percentageformatted,feedback,gradedategraded}]}]` |
| `mod_forum_get_forums_by_courses` | `courseids[]?` | `[{id,course,type,name,intro,cmid,numdiscussions}]` |
| `mod_forum_get_forum_discussions` | `forumid`, `sortorder=-1`, `page=-1`, `perpage=0` | `discussions[{id,name,discussion,userid,created,modified,subject,message,attachments,userfullname,numreplies,pinned}]` (`_paginated` variant is not registered in 5.0) |
| `mod_forum_get_discussion_posts` | `discussionid`, `sortby`, `sortdirection` | posts |
| `message_popup_get_popup_notifications` | `useridto` (0 = current), `newestfirst`, `limit=0`, `offset=0` | `notifications[{id,subject,text,fullmessage,smallmessage,contexturl,timecreated,timeread,read,component,eventtype}], unreadcount` |
| `mod_quiz_get_quizzes_by_courses` | `courseids[]?` | `quizzes[{id,coursemodule,course,name,intro,timeopen,timeclose,timelimit,attempts,grademethod,grade}]` — metadata only; never call `mod_quiz_start_attempt` |

Batching: `tool_mobile_call_external_functions` exists but is typed `write`; this client does not use it.

## 6. File download

- `fileurl` values are built with `file_encode_url("$CFG->wwwroot/webservice/pluginfile.php", …)`, e.g.
  `{site}/webservice/pluginfile.php/{contextid}/mod_resource/content/{rev}/{path}{file}?forcedownload=1`
  (with `slasharguments` off: `…pluginfile.php?file=/ctx/…&forcedownload=1`).
- `webservice/pluginfile.php` requires `token`: append `&token=T` if the URL already has `?`, else `?token=T`.
  The service needs `downloadfiles=1` (the mobile service has it; check `downloadfiles` in site info).
  Errors are JSON, e.g. `errorcode: invalidtoken`.

## 7. Site-wide `.ics` export

- `{site}/calendar/export_execute.php?userid=ID&authtoken=TOKEN&preset_what=all&preset_time=recentupcoming`.
  `preset_what ∈ all|user|groups|courses|categories`; `preset_time ∈ weeknow|weeknext|monthnow|monthnext|recentupcoming|custom`.
  Requires `$CFG->enablecalendarexport`; failures print plain text (`Invalid authentication`), not JSON.
- `authtoken = sha1(userid . passwordhash . calendar_exportsalt)` (`calendar/lib.php::calendar_get_export_token`)
  — stable until the password changes. Obtain via `core_calendar_get_calendar_export_token`.

## 8. Limits, expiry, invalid tokens

- No rate limiting in core web services (**absence unverified**). `external_tokens.lastaccess` is written at
  most every 60 s.
- Expiry: auto-created tokens get `validuntil = timecreated + $CFG->tokenduration` (default 12 weeks).
  `login/token.php` reuses the newest valid token and deletes expired ones.
- Invalid token: `{"exception":"moodle_exception","errorcode":"invalidtoken","message":"Invalid token - token not found"}`.
  Expired token: `{"exception":"webservice_access_exception","errorcode":"accessexception","message":"Access control exception"}`
  and the row is deleted. Treat both as "re-authenticate". Others: `sitemaintenance`, `usernotconfirmed`,
  `wsaccessusersuspended`, `wsaccessusernologin`, `passwordisexpired`.
- Docs: https://docs.moodle.org/en/Using_web_services · https://docs.moodle.org/en/Moodle_app_guide_for_admins
