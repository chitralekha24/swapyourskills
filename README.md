# SwapYourSkills

A full-stack skill exchange web application that lets users list skills they can teach, browse skills they want to learn, and connect with compatible matches — built end-to-end with Flask.

## Features

- **User Authentication** — secure sign-up/login with hashed passwords (Werkzeug)
- **Profile Management** — users can list skills offered and skills wanted
- **Bidirectional Skill Matching** — cross-queries offer/learn tables to detect compatible pairs
- **Email Notifications** — automated match alerts via Flask-Mail (Gmail SMTP)
- **Request Lifecycle** — full flow from send → accept/decline → rating, with session-based auth and duplicate-match prevention
- **Dynamic UI** — server-rendered templates with Jinja2, styled using Bootstrap 5

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite, SQLAlchemy (ORM)
- **Email:** Flask-Mail (Gmail SMTP)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, Jinja2 templating

## How It Works

1. Users sign up and create a profile listing skills they can teach and skills they want to learn.
2. The matching algorithm cross-references offer/learn tables across all users to surface compatible pairs.
3. When a match is found, both users are notified by email.
4. Users can send a skill-swap request, which the other party can accept or decline.
5. After a swap is completed, both users can rate each other.

---
Built by V. S. Chitralekha
