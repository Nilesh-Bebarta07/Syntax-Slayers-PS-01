# Campus Fix: Smart Campus Issue Reporting & Resolution System

Hackathon project for **PS-01**. Students and staff report campus problems (broken lights, water leakage, cleanliness, network issues, damaged equipment). Admins assign each complaint to a department and track it until it is resolved.

## Features

**Everyone**
- Sign up and log in
- Role-based screens: users and admins see different pages

**Students and staff (user)**
- Submit a complaint with title, description, category, location and an optional photo
- See all their previous complaints
- Track each complaint through four stages: Submitted, Assigned, In progress, Resolved
- See which department a complaint is assigned to

**Admin**
- See all complaints from all users
- Assign complaints to a department
- Change complaint status
- Filter by status, category and location
- Dashboard with basic statistics (total, waiting, being handled, resolved)

## Tech stack

| Part | Technology |
|------|------------|
| Frontend | HTML, CSS, JavaScript (no framework) |
| Backend | Python, FastAPI, Uvicorn |
| Database | MongoDB Atlas (planned, see [Current status](#current-status)) |

## Project structure

```
PS01/
├── backend/
│   ├── main.py          # FastAPI app: signup, login, session check
│   └── .env             # secrets such as the MongoDB connection string (never commit)
├── frontend/
│   ├── index.html       # login/signup screen, user view, admin view
│   ├── style.css        # all styling
│   └── app.js           # app logic and backend requests
└── README.md
```

## Getting started

### Requirements
- Python 3.9 or newer (during install, tick "Add Python to PATH")
- A modern browser (Edge or Chrome)
- Optional: VS Code with the Live Server extension

### 1. Run the backend

```
cd backend
pip install fastapi uvicorn
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/docs` to try the endpoints in the browser.

If `python` or `pip` is not recognized on Windows, use `py -m pip ...` and `py -m uvicorn ...`.

### 2. Run the frontend

Open `frontend/index.html` in your browser. If requests to the backend are blocked, right-click `index.html` in VS Code and choose **Open with Live Server**.

The frontend expects the backend at `http://127.0.0.1:8000`. To change this, edit the `API_URL` line near the top of `app.js`.

### 3. Log in

Demo admin account:

| Email | Password |
|-------|----------|
| `admin@campus.edu` | `admin123` |

Anyone who signs up through the form becomes a regular user. Admin accounts can only be created on the backend.

## API endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Welcome message | No |
| POST | `/signup` | Create a user account. Body: `name`, `email`, `password`. Returns `token` and `user`. | No |
| POST | `/login` | Log in. Body: `email`, `password`. Returns `token` and `user`. | No |
| GET | `/me` | Return the logged-in user | Bearer token |

The `user` object contains `id`, `name`, `email` and `role` (`"user"` or `"admin"`). Send the token in the header `Authorization: Bearer <token>`.

## Current status

Done:
- Full frontend: login/signup, complaint form, complaint history, admin dashboard, filters, status and department updates
- Backend authentication connected to the frontend

Not done yet:
- **Complaints are stored in the browser (localStorage), not on the server.** An admin only sees complaints created in the same browser.
- **Users and sessions are stored in memory on the backend.** They disappear when the server restarts.
- Passwords are hashed on the backend, but the backend has no rate limiting or password reset.

## Next steps

1. **Connect MongoDB Atlas.** Use PyMongo. Store `users`, `sessions` and `complaints` in the database. Keep the connection string in `backend/.env`.
2. **Add complaint endpoints** to the backend:
   - create a complaint (logged-in users)
   - list my complaints (users)
   - list all complaints (admin only)
   - update status and department (admin only)
3. **Switch `app.js`** so `listComplaints`, `createComplaint` and `updateComplaint` call those endpoints instead of using localStorage.
4. **Bonus features** from the problem statement: AI complaint categorization, automatic priority detection, campus map, duplicate detection, email alerts, resolution-time analytics.

## Security notes

- Never commit `.env` to GitHub. Add it to `.gitignore`.
- Before deploying, change the CORS setting in `main.py` from allowing every origin to allowing only your frontend address.
- Change the demo admin password before any real use.
- In MongoDB Atlas, remove "allow access from anywhere" once the project is finished.

## Team

- Frontend: _add name_
- Backend: _add name_