# NerDecks

A spaced repetition web application that helps users remember information efficiently by reviewing cards at scientifically optimized intervals.

---

# Table Of Contents

- Design & Planning  
- Features  
- Technologies Used  
- Testing  
- Bugs  
- Deployment  
- AI  
- Credits  

---

# Design & Planning

## User Stories

### Core Learning Flow
- As a user, I want to create an account so I can save my decks and cards.
- As a user, I want to log in securely so I can access my personal learning material.
- As a user, I want to create decks so I can organize topics.
- As a user, I want to create cards inside decks so I can study specific content.
- As a user, I want to review cards using spaced repetition so I can remember them long term.
- As a user, I want to mark cards as correct or incorrect so the system can adjust review timing.
- As a user, I want to see only my own decks and cards.
- As a user, I want a clean and minimal interface so I can focus on studying.

---

## Wireframes

For the design of the wire frame I used Adobe XD.

<img src="static/images/documentation/Wireframe.png" alt="NerDeck wireframe">



---

## Agile Methodology

The project was developed using an iterative Agile approach:

- Features were broken down into user stories.
- Stories were grouped into iterations (MVP first).
- Tasks were created for:
  - Models
  - Views
  - Templates
  - Spaced repetition logic
  - Authentication
  - UI improvements

Kanban board structure:
- Backlog  
- To Do  
- In Progress  
- Testing  
- Done  

<img src="static/images/documentation/kanban_nerdeck.png" alt="kanban image of nerdeck workflow">

---

## Typography

The project uses:

- Inter – for clean, readable UI text
- Space Grotesk – for headings and branding
- Fredoka – for playful brand personality

These fonts were chosen for clarity and modern appearance.

<img src="static/images/documentation/fonts_nerdecks.png" alt="Images of fonts from google fonts">

---

## Colour Scheme

Primary:
- White (#FFFFFF)
- Light Gray (Bootstrap light backgrounds)

Accent:
- Blue (Bootstrap primary)
- Custom brand colors for NerDeck logo

Coolors.co was used as reference for quick colors pallete selection.

<img src="static/images/documentation/palettes_nerdecks.png" alt="Screenshot from coolors.co" >


---

## Database Diagram

Main models:

- User (Django built-in)
- Deck
  - name
  - user (ForeignKey → User)

- Card
  - deck (ForeignKey → Deck)
  - front
  - back
  - step
  - due_at
  - created_at

Relationships:

- One User → Many Decks  
- One Deck → Many Cards  
- One Card → Belongs to exactly one Deck  

<img src="static/images/documentation/erd_nerdecks.png" alt="Screenshot of NerDeck app ERD">

---

# Features

## Navigation

- Responsive top navigation
- Links change depending on authentication status
- Clean minimal layout

---

## Footer

- Simple copyright section
- Consistent across all pages

---

## Home Page

- Explanation of spaced repetition
- Call to action (Create account)
- Minimal visual storytelling

---

## CRUD Functionality

### Deck
- Create deck
- View deck
- Delete deck

### Card
- Create card
- Review card
- Delete card

Cards are filtered by logged-in user.

---

## Authentication & Authorisation

- Django authentication system
- Login / Logout
- Signup
- User-based data isolation

---

# Technologies Used

- Python
- Django
- HTML5
- CSS3
- Bootstrap 5
- JavaScript (ES6 modules)
- SQLite (development)
- PostgreSQL (production)
- Heroku
- Git & GitHub

---

## Libraries

- Bootstrap
- GSAP
- Django built-in auth
- WhiteNoise
- Gunicorn

---

# Testing

## Google Lighthouse Performance

(Screenshots to be added)

---

## Browser Compatibility

Tested on:
- Chrome
- Safari
- Edge
- Firefox

---

## Responsiveness

Tested on:
- Mobile
- Tablet
- Desktop

---

## Code Validation

Validated:

- HTML → W3C Validator
- CSS → W3C Validator
- JS → JSHint
- Python → PEP8

---

## Manual Testing – User Stories

| User Story | Test | Pass |
|------------|------|------|
| Create account | User fills signup form and is redirected | ✓ |
| Login | User logs in with valid credentials | ✓ |
| Create deck | User submits deck form | ✓ |
| Create card | User submits card form | ✓ |
| Review card | User marks correct/incorrect | ✓ |

---

## Manual Testing – Features

| Feature | Action | Status |
|----------|--------|--------|
| Deck creation | Submit valid form | ✓ |
| Card filtering by user | Login as different user | ✓ |
| Admin filtering | Filter cards by username | ✓ |
| Spaced repetition logic | Correct answer increases interval | ✓ |

---

# Bugs

- Cards not filtered by user in admin → Fixed via admin configuration.
- Redundant user column in admin table → Cleaned configuration.
- Git push conflicts → Resolved with pull and merge.
- Static files not loading in production → Fixed via WhiteNoise.

---

# Deployment

This website is deployed to Heroku from a GitHub repository.

## Creating Repository on GitHub

1. Create repository.
2. Clone locally.
3. Develop project.
4. Push to GitHub.

## Creating an App on Heroku

1. Log in to Heroku.
2. Create new app.
3. Connect GitHub repository.

## Database

- Created PostgreSQL database.
- Set DATABASE_URL in env.py and Heroku config vars.

## Config Vars

- DATABASE_URL
- SECRET_KEY
- CLOUDINARY_URL
- PORT = 8000

## Deployment

- Manual deploy from Heroku dashboard.
- Deploy branch.
- View app.

---

# AI

AI was used for:

- Explaining Django concepts
- Debugging admin and model structure
- Improving UI structure
- Implementing spaced repetition logic

---

# Credits

- Django documentation
- Bootstrap documentation
- GSAP documentation
- Google Fonts
- Code Institute deployment guide
- OpenAI
