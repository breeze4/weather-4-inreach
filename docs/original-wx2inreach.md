WX2InReach Self-Hosted Spec
What It Actually Does

Poll a Gmail inbox for emails from Garmin InReach devices
Extract GPS coordinates from those emails (either from the email body or a linked Garmin page)
Parse command keywords from the message body
Fetch weather from NWS or VisualCrossing
Format forecast into ≤160-char messages
Reply to the sender's email address (which routes back to their InReach)


InReach Email Format
This is the trickiest part. InReach emails contain a Garmin-hosted URL in the body, e.g.:
https://share.garmin.com/TextMessage/TxtMsg?extId=XXXXXXXX
That page contains the device's GPS coordinates. The history of the service shows Garmin has changed this format ~5 times, so you need to handle this defensively. You'll need to:

Extract the Garmin share link from the email body (regex on share.garmin.com or explore.garmin.com)
Fetch that page and scrape lat/lon out of it
Also attempt to parse lat/lon directly from the email body as a fallback (some formats include it inline)

Red flag to investigate before writing code: You don't yet know the current exact format of that Garmin page. You'll need to send yourself an actual InReach email and inspect both the raw email and the linked page before you can write a reliable parser. This is the single biggest unknown.

Command Parsing
From the email body text, parse these keywords (case-insensitive):
KeywordMeaningwx nowRequired base commandnws6NWS 6-hourly detailed (US only)nws6 allNWS 6-hourly, 72h (2-3 reply messages)vcForce VisualCrossing for US locationsvc allVisualCrossing 6-day (may send multiple)vc siVisualCrossing in metricloc {lat} {lon}Override GPS with explicit coordinates
Routing logic:
if "loc" keyword → use provided lat/lon
else → use lat/lon from InReach email

if US location:
  default → NWS 12-hourly
  "nws6" → NWS 6-hourly
  "vc" → VisualCrossing
else:
  default → VisualCrossing
  "nws6" → VisualCrossing (NWS not available)
US location = lat between 24-50, lon between -125 and -66 (rough continental US bounding box; also need to handle AK/HI).

Weather APIs
NWS (US)
GET https://api.weather.gov/points/{lat},{lon}
→ returns JSON with:
    properties.forecast         (12-hourly URL)
    properties.forecastHourly   (hourly URL, use for nws6)

GET {forecast URL}
→ returns periods array: name, temperature, windSpeed, windDirection, shortForecast
No API key required. Free. Rate limit: be reasonable.
VisualCrossing
GET https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}
  ?key={API_KEY}
  &unitGroup=us      (or "metric" for "si" flag)
  &include=days,hours
  &contentType=json
Free tier: 1000 records/day. You'll need to sign up for a key at visualcrossing.com.

Message Formatting
The hard constraint: 160 characters per message (SMS segment size, since InReach uses satellite messaging billed per segment).
NWS 12-hourly format (target: 4-5 days in one message):
Mon Hi62 Sunny. Tue Hi58/Lo44 PM Rain. Wed Hi55/Lo40 Cloudy. Thu Hi60 Clear.
NWS 6-hourly format (target: 36-48h, possibly 2-3 messages):
Mon6a: W10 48F Cloudy. Mon12p: SW15 55F PCldy. Mon6p: SW10 52F Rain.
VisualCrossing format:
Mon 6a:55F W12. 2p:68F SW15. 10p:58F NW8. Tue 6a:48F N10. 2p:62F W14.
You'll need an abbreviation dictionary for condition descriptions. Build it from NWS shortForecast strings and VisualCrossing conditions field. At minimum:
pythonABBREVS = {
    "Partly Cloudy": "PCldy",
    "Mostly Cloudy": "MCldy",
    "Chance Rain Showers": "ChRain",
    "Thunderstorms": "Tstms",
    "Snow Showers": "SnShwrs",
    # etc.
}

Architecture
Recommend Python, deployed on a small VPS or even a Raspberry Pi.
├── main.py           # entry point, cron target (poll every 5 min)
├── email_client.py   # Gmail IMAP read + SMTP send
├── inreach_parser.py # parse InReach email, extract GPS from Garmin page
├── command_parser.py # parse "wx now nws6 loc ..." etc.
├── nws.py            # NWS API calls
├── visualcrossing.py # VisualCrossing API calls
├── formatter.py      # pack forecast into ≤160 char strings
├── config.py         # email creds, VC API key, etc.
Gmail setup: Create a dedicated Gmail account. Use App Passwords (not OAuth) for simplicity, enable IMAP. Or use Gmail API with a service account.
Mark emails as read after processing so you don't reprocess.

Error Handling
Reply with terse error messages that fit in one InReach message:
ConditionReplyNo GPS in emailError: No GPS location in requestloc parse failError: Bad lat/lon. Use: loc 36.58 -118.29NWS no dataError: NWS no data for this locationVC API failError: VC forecast unavailable, try againNot an InReach emailIgnore silently (don't reply)

Known Risks / Things to Validate First

Garmin page format — you must inspect a real InReach email before writing the parser. This has broken the original service 5+ times.
VisualCrossing free tier — 1000 records/day. If you share the service with others, this could be an issue. Paid tier is cheap ($0.0001/record).
Email deliverability — outgoing replies from a new Gmail address may hit spam filters on the receiving Garmin infrastructure. Worth testing before relying on it in the field.
US boundary detection — the bounding box approach misses Hawaii, Alaska, Puerto Rico. Use a proper point-in-polygon check or just call both APIs and use NWS response as the discriminator (it returns an error for non-US points).
"nws6" outside US — the original routed this to VisualCrossing (not DarkSky anymore). Make sure your implementation does the same.


What You Need Before Starting

A Garmin InReach device to test with (or access to someone's)
Raw email from InReach (view source) + the linked Garmin page HTML
VisualCrossing API key (free signup)
A Gmail account dedicated to this