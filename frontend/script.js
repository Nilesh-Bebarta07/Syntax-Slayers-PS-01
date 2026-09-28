/* =========================================================
   Campus Fix: frontend logic
   ---------------------------------------------------------
   All data lives in localStorage through the `api` object
   below, so the UI works with no backend. When your backend
   is ready, replace the body of each api.* function with a
   fetch() call and keep the rest of the file as it is.

   DEMO ONLY: passwords are stored as plain text here.
   The real backend must hash them (bcrypt) and issue a
   token or session cookie.
   ========================================================= */

const CATEGORIES = ["Electrical", "Water & Plumbing", "Cleanliness", "Network & IT", "Furniture & Equipment", "Other"];
const STATUSES = ["Submitted", "Assigned", "In progress", "Resolved"];
const DEPARTMENTS = ["Electrical", "Plumbing", "Housekeeping", "IT Services", "Maintenance"];

const KEYS = { users: "cf_users", complaints: "cf_complaints", session: "cf_session" };

/* ---------- Data layer (swap these for fetch() calls later) ---------- */
const store = {
  read(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  },
  write(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
};

const api = {
  seed() {
    const users = store.read(KEYS.users, []);
    if (!users.some(u => u.role === "admin")) {
      users.push({ id: "u_admin", name: "Campus Admin", email: "admin@campus.edu", password: "admin123", role: "admin" });
      store.write(KEYS.users, users);
    }
  },

  signup({ name, email, password }) {
    const users = store.read(KEYS.users, []);
    if (users.some(u => u.email === email)) throw new Error("An account with this email already exists. Log in instead.");
    // New sign-ups are always regular users. Admins are created by the backend.
    const user = { id: "u_" + Date.now(), name, email, password, role: "user" };
    users.push(user);
    store.write(KEYS.users, users);
    return publicUser(user);
  },

  login({ email, password }) {
    const user = store.read(KEYS.users, []).find(u => u.email === email && u.password === password);
    if (!user) throw new Error("Email or password is incorrect. Check both and try again.");
    return publicUser(user);
  },

  listComplaints({ userId } = {}) {
    const all = store.read(KEYS.complaints, []);
    const rows = userId ? all.filter(c => c.userId === userId) : all;
    return rows.sort((a, b) => b.createdAt - a.createdAt);
  },

  createComplaint(user, data) {
    const all = store.read(KEYS.complaints, []);
    const complaint = {
      id: "c_" + Date.now(),
      userId: user.id,
      userName: user.name,
      ...data,
      status: "Submitted",
      department: "",
      createdAt: Date.now()
    };
    all.push(complaint);
    store.write(KEYS.complaints, all);
    return complaint;
  },

  updateComplaint(id, changes) {
    const all = store.read(KEYS.complaints, []);
    const item = all.find(c => c.id === id);
    if (!item) return;
    Object.assign(item, changes);
    store.write(KEYS.complaints, all);
    return item;
  }
};

const publicUser = ({ id, name, email, role }) => ({ id, name, email, role });

/* ---------- Helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, ch =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

const fmtDate = (t) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

const statusClass = (s) => ({ "Submitted": "", "Assigned": "assigned", "In progress": "progress", "Resolved": "resolved" }[s]);

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function clearError(el) { el.hidden = true; el.textContent = ""; }

let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 2600);
}

/* Shrinks the photo so it fits in localStorage. A real backend would take the original file. */
function fileToDataURL(file, maxSide = 800) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read that photo. Try a different file."));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("That file is not a valid image."));
      img.onload = () => {
        const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.7));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

/* ---------- Session ---------- */
let currentUser = null;

function setSession(user) {
  currentUser = user;
  store.write(KEYS.session, user);
  renderApp();
}

function logout() {
  currentUser = null;
  localStorage.removeItem(KEYS.session);
  renderApp();
}

/* ---------- Auth screen ---------- */
function initAuth() {
  const tabs = { login: $("#tab-login"), signup: $("#tab-signup") };
  const forms = { login: $("#login-form"), signup: $("#signup-form") };
  const errorEl = $("#auth-error");

  function switchTab(name) {
    for (const key of Object.keys(tabs)) {
      const active = key === name;
      tabs[key].classList.toggle("active", active);
      tabs[key].setAttribute("aria-selected", active);
      forms[key].hidden = !active;
    }
    clearError(errorEl);
  }
  tabs.login.addEventListener("click", () => switchTab("login"));
  tabs.signup.addEventListener("click", () => switchTab("signup"));

  forms.login.addEventListener("submit", (e) => {
    e.preventDefault();
    clearError(errorEl);
    const f = new FormData(forms.login);
    const email = f.get("email").trim().toLowerCase();
    const password = f.get("password");
    if (!email || !password) return showError(errorEl, "Enter your email and password.");
    try {
      setSession(api.login({ email, password }));
      forms.login.reset();
    } catch (err) { showError(errorEl, err.message); }
  });

  forms.signup.addEventListener("submit", (e) => {
    e.preventDefault();
    clearError(errorEl);
    const f = new FormData(forms.signup);
    const name = f.get("name").trim();
    const email = f.get("email").trim().toLowerCase();
    const password = f.get("password");
    if (!name) return showError(errorEl, "Enter your full name.");
    if (!/^\S+@\S+\.\S+$/.test(email)) return showError(errorEl, "Enter a valid email address.");
    if (password.length < 6) return showError(errorEl, "Use a password with at least 6 characters.");
    try {
      setSession(api.signup({ name, email, password }));
      forms.signup.reset();
      toast("Account created. Welcome, " + name.split(" ")[0] + ".");
    } catch (err) { showError(errorEl, err.message); }
  });
}

/* ---------- App shell (role-based) ---------- */
function renderApp() {
  const loggedIn = !!currentUser;
  $("#auth-view").hidden = loggedIn;
  $("#app-view").hidden = !loggedIn;
  if (!loggedIn) return;

  const isAdmin = currentUser.role === "admin";
  $("#who").textContent = currentUser.name;
  $("#role-badge").textContent = isAdmin ? "Admin" : "Student / Staff";
  $("#user-panel").hidden = isAdmin;
  $("#admin-panel").hidden = !isAdmin;

  if (isAdmin) renderAdmin(); else renderUser();
}

/* ---------- User panel ---------- */
function statusTrack(status) {
  const idx = STATUSES.indexOf(status);
  return `<ol class="track" aria-label="Progress: ${esc(status)}">` +
    STATUSES.map((s, i) => `<li class="${i <= idx ? "done" : ""} ${i === idx ? "current" : ""}">${s}</li>`).join("") +
    `</ol>`;
}

function ticketHTML(c, { admin = false } = {}) {
  const sc = statusClass(c.status);
  return `
    <article class="ticket ${sc ? "s-" + sc : ""}" data-id="${esc(c.id)}">
      <div class="ticket-head">
        <h3>${esc(c.title)}</h3>
        <span class="badge ${sc ? "status-" + sc : ""}">${esc(c.status)}</span>
      </div>
      <div class="ticket-meta">
        <span>Category: ${esc(c.category)}</span>
        <span>Location: ${esc(c.location)}</span>
        <span>Reported ${fmtDate(c.createdAt)}${admin ? " by " + esc(c.userName) : ""}</span>
      </div>
      <p>${esc(c.description)}</p>
      ${c.photo ? `<img class="evidence" src="${c.photo}" alt="Photo evidence for ${esc(c.title)}">` : ""}
      ${admin ? adminControls(c) : `
        ${statusTrack(c.status)}
        <p class="assigned">${c.department ? "Assigned to " + esc(c.department) : "Waiting to be assigned"}</p>`}
    </article>`;
}

function renderUser() {
  const list = api.listComplaints({ userId: currentUser.id });
  $("#my-complaints").innerHTML = list.length
    ? list.map(c => ticketHTML(c)).join("")
    : `<div class="empty">You have not reported anything yet. Use the form to submit your first complaint.</div>`;
}

function initUserForm() {
  const form = $("#complaint-form");
  const errorEl = $("#complaint-error");
  const preview = $("#photo-preview");

  form.category.innerHTML = CATEGORIES.map(c => `<option>${esc(c)}</option>`).join("");

  form.photo.addEventListener("change", () => {
    const file = form.photo.files[0];
    if (!file) { preview.hidden = true; return; }
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError(errorEl);
    const f = new FormData(form);
    const title = f.get("title").trim();
    const location = f.get("location").trim();
    const description = f.get("description").trim();
    if (!title || !location || !description) return showError(errorEl, "Fill in the title, location and description.");

    let photo = "";
    const file = form.photo.files[0];
    if (file) {
      try { photo = await fileToDataURL(file); }
      catch (err) { return showError(errorEl, err.message); }
    }

    try {
      api.createComplaint(currentUser, { title, location, description, category: f.get("category"), photo });
    } catch {
      return showError(errorEl, "Could not save the complaint. Remove the photo or clear old data, then try again.");
    }
    form.reset();
    preview.hidden = true;
    renderUser();
    toast("Complaint submitted.");
  });
}

/* ---------- Admin panel ---------- */
function adminControls(c) {
  return `
    <div class="admin-controls">
      <label>Status
        <select data-action="status">
          ${STATUSES.map(s => `<option ${s === c.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
      </label>
      <label>Assign to
        <select data-action="department">
          <option value="">Unassigned</option>
          ${DEPARTMENTS.map(d => `<option ${d === c.department ? "selected" : ""}>${d}</option>`).join("")}
        </select>
      </label>
    </div>`;
}

function renderAdmin() {
  const all = api.listComplaints();
  const fStatus = $("#f-status").value;
  const fCategory = $("#f-category").value;
  const fLocation = $("#f-location").value.trim().toLowerCase();

  const count = (s) => all.filter(c => c.status === s).length;
  $("#stats").innerHTML = `
    <div class="stat total"><b>${all.length}</b><span>Total complaints</span></div>
    <div class="stat"><b>${count("Submitted")}</b><span>Waiting to be assigned</span></div>
    <div class="stat"><b>${count("In progress") + count("Assigned")}</b><span>Being handled</span></div>
    <div class="stat"><b>${count("Resolved")}</b><span>Resolved</span></div>`;

  const rows = all.filter(c =>
    (!fStatus || c.status === fStatus) &&
    (!fCategory || c.category === fCategory) &&
    (!fLocation || c.location.toLowerCase().includes(fLocation)));

  $("#all-complaints").innerHTML = rows.length
    ? rows.map(c => ticketHTML(c, { admin: true })).join("")
    : `<div class="empty">${all.length ? "No complaints match these filters. Clear a filter to see more." : "No complaints have been submitted yet."}</div>`;
}

function initAdmin() {
  $("#f-status").innerHTML += STATUSES.map(s => `<option>${s}</option>`).join("");
  $("#f-category").innerHTML += CATEGORIES.map(c => `<option>${esc(c)}</option>`).join("");
  ["#f-status", "#f-category"].forEach(id => $(id).addEventListener("change", renderAdmin));
  $("#f-location").addEventListener("input", renderAdmin);

  // One listener handles every complaint's dropdowns
  $("#all-complaints").addEventListener("change", (e) => {
    const action = e.target.dataset.action;
    if (!action) return;
    const id = e.target.closest(".ticket").dataset.id;
    const changes = {};

    if (action === "status") changes.status = e.target.value;
    if (action === "department") {
      changes.department = e.target.value;
      // Assigning a department moves a new complaint to "Assigned"
      const current = api.listComplaints().find(c => c.id === id);
      if (e.target.value && current.status === "Submitted") changes.status = "Assigned";
    }
    api.updateComplaint(id, changes);
    renderAdmin();
    toast(action === "status" ? "Status updated." : "Department assigned.");
  });
}

/* ---------- Boot ---------- */
document.addEventListener("DOMContentLoaded", () => {
  api.seed();
  initAuth();
  initUserForm();
  initAdmin();
  $("#logout-btn").addEventListener("click", logout);

  currentUser = store.read(KEYS.session, null);
  renderApp();
});