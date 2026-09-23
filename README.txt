A320 ATQ 2026 - Group Vote
===========================

WHAT THIS IS
A small website containing all 35 questions from your PDF, that you run on
your own Windows computer. Your friends open it in a browser - on the same Wi-Fi/network, or from
anywhere if you add a tunnel (see below) - to pick their answer for each
question. Everyone sees a live
tally of how many people voted for each option, plus who voted for what,
and can leave comments per question.

REQUIREMENTS
- Python 3 installed on the Windows computer that will host it.
  Check by opening Command Prompt and typing: python --version
  If it's not installed, get it from https://www.python.org/downloads/
  (tick "Add python.exe to PATH" during install).
- No other installs needed - the app only uses Python's built-in libraries.

HOW TO RUN IT
1. Put app.py in any folder on the host computer.
2. Open Command Prompt, cd into that folder, and run:
       python app.py
3. It will print two links, e.g.:
       On this computer:      http://localhost:8000
       For your friends:      http://192.168.1.42:8000
4. Share the second link with your friends - they must be on the same
   Wi-Fi/network (e.g. same home or office network). They open it in any
   browser, phone or laptop.
5. Windows may show a firewall prompt the first time - click "Allow access"
   (at least for Private networks) so others can reach the server.

LETTING FRIENDS JOIN FROM ANYWHERE (NOT JUST YOUR WI-FI)
If everyone needs to access it over the internet (different networks,
different cities, etc.), keep app.py running as above, then use a free
tunnel tool to get a public link. No router setup or port forwarding
needed - this works from behind almost any home/office network.

Option A - Cloudflare Tunnel (recommended, no account needed):
1. Download cloudflared for Windows:
   https://github.com/cloudflare/cloudflared/releases/latest
   (grab the file named cloudflared-windows-amd64.exe)
2. Rename it to cloudflared.exe and put it in the same folder as app.py
   (or anywhere convenient).
3. With app.py already running in one Command Prompt window, open a
   second Command Prompt in that folder and run:
       cloudflared.exe tunnel --url http://localhost:8000
4. It will print a public link like:
       https://random-words-1234.trycloudflare.com
   Share that link with your friends - it works from anywhere, on any
   network, no login required on their end.
5. Keep both Command Prompt windows open (app.py and cloudflared) for as
   long as you want the site reachable. Closing either one ends it.
   Note: this free "quick tunnel" link changes each time you restart
   cloudflared, so re-share it if you stop and start again.

Option B - ngrok (alternative, free account required):
1. Sign up free at https://ngrok.com and download ngrok for Windows.
2. Run once: ngrok config add-authtoken YOUR_TOKEN (token shown on your
   ngrok dashboard).
3. With app.py running, in a second Command Prompt run:
       ngrok http 8000
4. Share the https://....ngrok-free.app link it prints. Same caveat -
   the link changes each time you restart ngrok on the free plan.

Either option means your Windows PC still does all the work (it must
stay on and awake) - the tunnel just gives it a public address.

HOSTING IT ONLINE FOR FREE (NO PC REQUIRED TO STAY ON)
If you'd rather not keep your own computer running, Render.com will host
this for free - good enough for a handful of people voting.

1. Create a free GitHub account (github.com) if you don't have one, make a
   new repository, and upload app.py to it (no other files needed).
2. Create a free Render account at render.com and sign in with GitHub.
3. Click "New +" -> "Web Service", pick the repository you just made.
4. Settings:
       Runtime: Python 3
       Build Command: (leave blank)
       Start Command: python app.py
       Instance Type: Free
5. Click "Create Web Service". After a minute or two you'll get a link
   like https://your-app-name.onrender.com - that's the address to share
   with friends, from anywhere, permanently (no cloudflared/ngrok needed).

Two things to know about the free tier:
- It goes to sleep after 15 minutes with no visitors, so the first person
  to open the link after a quiet spell waits ~30-50 seconds for it to
  wake up. After that it's instant for everyone.
- Votes/comments are stored in a file on Render's disk, which is wiped if
  you push a new deploy (editing and re-uploading app.py). It's fine for
  running the quiz in one sitting; don't rely on it as long-term storage.

If you outgrow the free tier (want it always-on and never wiped), Render's
cheapest paid plan is around $7/month, or a small VPS (e.g. a $4-6/month
droplet on DigitalOcean or Hetzner) works too - just upload app.py and run
"python3 app.py" there.

USING IT
- Everyone types their name once at the top (saved in their browser).
- Tap/click an option to vote - it updates instantly for everyone.
- Voting again for the same question changes your previous vote (one vote
  per person per question).
- Names of who voted for each option are shown under the bar, so you can
  see at a glance if you all agree.
- Each question has a collapsible Comments section to discuss before
  settling on an answer.

AUDIT LOG / SPOTTING A DODGY VOTER / BACKING UP BEFORE A REDEPLOY
The live results only ever show each person's latest answer - if someone
changes their vote, the old one is overwritten. To see the FULL history
(every vote and comment ever submitted, with timestamps and the voter's
IP address), two things are kept:

- A file called audit_log.txt appears next to app.py - plain text, one
  line per event, easy to skim by eye. Useful for e.g. spotting someone
  who flip-flopped between answers, or several "different" names voting
  from the same IP address.
- Visiting /export in a browser (e.g. https://your-app.onrender.com/export
  or http://localhost:8000/export) downloads the same data as a CSV file
  you can open in Excel/Sheets - columns are timestamp, event_type,
  question_id, voter, value, ip_address.

This /export link isn't password protected, so anyone with the link could
view it - fine for a casual friend group, but don't rely on it if you'd
mind a curious friend peeking at the raw log.

Because Render's free tier wipes its disk on every redeploy, download a
fresh copy from /export (or grab audit_log.txt if running locally) BEFORE
you push any change that triggers a redeploy, so you keep a permanent
record even though the live site's data resets.

STOPPING / DATA
- Press Ctrl+C in the Command Prompt window to stop the server.
- All votes and comments are stored in a file called quiz_votes.db that
  appears next to app.py. Delete it to reset everything, or back it up to
  keep a record.
- This is intended for a local/trusted network - there's no login system,
  so treat it as a casual group tool rather than a public website.

CUSTOMIZING
- To change the port (e.g. if 8000 is in use), edit the line
  "PORT = 8000" near the top of app.py.
