import "./style.css";

const API_GATEWAY = window.API_BASE_URL || "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Tutorias</h1>
        <p>Los docentes publican horarios y los estudiantes reservan sesiones.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="/portal.html">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card" id="role-panel"></div>
      <div class="card">
        <h2>Sesiones disponibles</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="session-list" class="list"></div>
      </div>
      <div class="card">
        <h2>Detalle de sesion</h2>
        <div id="session-detail" class="list-item">Selecciona una sesion.</div>
      </div>
      <div class="card">
        <h2>Tickets emitidos</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-ticket-refresh">Actualizar</button>
        </div>
        <div id="ticket-list" class="list"></div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para gestionar tutorias.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const rolePanel = document.getElementById("role-panel");
const sessionList = document.getElementById("session-list");
const sessionDetail = document.getElementById("session-detail");
const ticketList = document.getElementById("ticket-list");

const params = new URLSearchParams(window.location.search);
if (params.get("token")) {
  localStorage.setItem("auth_token", params.get("token"));
  localStorage.setItem("auth_role", params.get("role") || "student");
  localStorage.setItem("auth_name", params.get("name") || "");
  window.history.replaceState({}, "", window.location.pathname);
}

const token = localStorage.getItem("auth_token");
const role = localStorage.getItem("auth_role") || "invitado";
const parseJwt = (tokenValue) => {
  try {
    const payload = tokenValue.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
};

const tokenPayload = token ? parseJwt(token) : {};
const email = localStorage.getItem("auth_email") || tokenPayload.email || "";
const name = localStorage.getItem("auth_name") || tokenPayload.name || "";
const displayStudent = name || email || "sin correo";
rolePill.textContent = `Rol: ${role}`;

const setStatus = (message, isError = false) => {
  statusEl.textContent = message;
  statusEl.style.borderLeftColor = isError ? "#b71c1c" : "var(--gold)";
  statusEl.style.color = isError ? "#7a1e1e" : "#7c2d12";
};

const request = async (method, path, body) => {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_GATEWAY}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok || !data.success) {
    throw new Error(data.message || "Error en la solicitud");
  }
  return data;
};

let selectedSessionId = null;
let sessionsCache = [];

const getAvailableSessions = () => sessionsCache.filter((s) => s.student.toUpperCase() === "DISPONIBLE");
const updateStudentSelectors = () => {
  const teacherFilter = document.getElementById("teacher-filter");
  const sessionSelect = document.getElementById("session-select");
  if (!teacherFilter || !sessionSelect) return;

  const availableSessions = getAvailableSessions();
  const teachers = Array.from(new Set(availableSessions.map((s) => s.teacher))).sort();
  teacherFilter.innerHTML = `<option value="">Todos</option>${teachers
    .map((teacher) => `<option value="${teacher}">${teacher}</option>`)
    .join("")}`;

  const filtered = teacherFilter.value
    ? availableSessions.filter((s) => s.teacher === teacherFilter.value)
    : availableSessions;
  const options = filtered
    .filter((s) => s.student.toUpperCase() === "DISPONIBLE")
    .map((s) => `<option value="${s.id}">#${s.id} - ${s.teacher} - ${s.date}</option>`)
    .join("");
  sessionSelect.innerHTML = options
    ? `<option value="">Selecciona una sesion</option>${options}`
    : "<option value=\"\">No hay sesiones disponibles</option>";

  selectedSessionId = null;
  const reserveButton = document.getElementById("btn-reserve");
  if (reserveButton) reserveButton.disabled = true;
};

const renderRolePanel = () => {
  if (role === "professor") {
    rolePanel.innerHTML = `
      <h2>Publicar horario</h2>
      <form id="prof-form">
        <label>Docente
          <input name="teacher" placeholder="Ing. Perez" value="${name}" required />
        </label>
        <label>Fecha y hora
          <input name="date" type="datetime-local" required />
        </label>
        <div class="actions">
          <button class="btn btn-primary" type="submit">Crear sesion</button>
        </div>
      </form>
      <p><small>Las sesiones se crean como DISPONIBLE.</small></p>
    `;
    document.getElementById("prof-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.target).entries());
      try {
        await request("POST", "/tutoring/api/tutorings", payload);
        setStatus("Horario publicado.");
        event.target.reset();
        await refreshList();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    return;
  }

  rolePanel.innerHTML = `
    <h2>Reservar tutoria</h2>
    <label>Docente
      <select id="teacher-filter">
        <option value="">Todos</option>
      </select>
    </label>
    <label>Horario disponible
      <select id="session-select">
        <option value="">Selecciona una sesion</option>
      </select>
    </label>
    <div class="actions">
      <button class="btn btn-primary" id="btn-reserve" disabled>Reservar</button>
    </div>
    <p><small>Estudiante: ${displayStudent}.</small></p>
  `;
  const teacherFilter = document.getElementById("teacher-filter");
  const sessionSelect = document.getElementById("session-select");
  updateStudentSelectors();

  teacherFilter.addEventListener("change", () => {
    updateStudentSelectors();
  });

  sessionSelect.addEventListener("change", () => {
    selectedSessionId = sessionSelect.value ? Number(sessionSelect.value) : null;
    document.getElementById("btn-reserve").disabled = !selectedSessionId;
  });
  document.getElementById("btn-reserve").addEventListener("click", async () => {
    if (!selectedSessionId) {
      setStatus("Selecciona una sesion para reservar.", true);
      return;
    }
    try {
      await request("POST", `/tutoring/api/tutorings/${selectedSessionId}/reserve`);
      setStatus("Tutoria reservada.");
      await refreshList();
      await refreshTickets();
      selectedSessionId = null;
      document.getElementById("btn-reserve").disabled = true;
    } catch (error) {
      setStatus(error.message, true);
    }
  });
};

const renderList = (items) => {
  if (!items.length) {
    sessionList.innerHTML = "<div class='list-item'>No hay sesiones disponibles.</div>";
    return;
  }
  sessionList.innerHTML = items
    .map((item) => {
      const disponible = item.student.toUpperCase() === "DISPONIBLE";
      return `
        <div class="list-item">
          <strong>Sesion #${item.id} - ${item.teacher}</strong>
          <span>Fecha: ${item.date}</span>
          <span>Estado: ${disponible ? "Disponible" : `Reservada por ${item.student}`}</span>
          ${
            role === "student" && disponible
              ? `<button class="btn btn-red" data-id="${item.id}">Seleccionar</button>`
              : ""
          }
        </div>
      `;
    })
    .join("");

  if (role === "student") {
    sessionList.querySelectorAll("button[data-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        selectedSessionId = Number(btn.dataset.id);
        const sessionSelect = document.getElementById("session-select");
        if (sessionSelect) {
          sessionSelect.value = btn.dataset.id;
          selectedSessionId = Number(btn.dataset.id);
          document.getElementById("btn-reserve").disabled = false;
        }
      });
    });
  }

  sessionList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      sessionDetail.innerHTML = `
        <strong>Sesion #${item.id}</strong>
        <span>Docente: ${item.teacher}</span>
        <span>Fecha: ${item.date}</span>
        <span>Estado: ${item.student}</span>
        ${
          role === "professor"
            ? `
          <div class="divider"></div>
          <label>Docente
            <input id="edit-teacher" value="${item.teacher}" />
          </label>
          <label>Fecha y hora
            <input id="edit-date" type="datetime-local" value="${item.date.replace(" ", "T")}" />
          </label>
          <div class="actions">
            <button class="btn btn-primary" id="btn-update-session">Actualizar</button>
            <button class="btn btn-outline" id="btn-delete-session">Eliminar</button>
          </div>
        `
            : ""
        }
      `;
      const updateButton = document.getElementById("btn-update-session");
      if (updateButton) {
        updateButton.addEventListener("click", async () => {
          const teacher = document.getElementById("edit-teacher").value.trim();
          const date = document.getElementById("edit-date").value;
          if (teacher.length < 2 || !date) {
            setStatus("Completa docente y fecha.", true);
            return;
          }
          try {
            await request("PUT", `/tutoring/api/tutorings/${item.id}`, { teacher, date });
            setStatus("Sesion actualizada.");
            await refreshList();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
      const deleteButton = document.getElementById("btn-delete-session");
      if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
          try {
            await request("DELETE", `/tutoring/api/tutorings/${item.id}`);
            setStatus("Sesion eliminada.");
            sessionDetail.innerHTML = "Selecciona una sesion.";
            await refreshList();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
    });
  });
};

const refreshList = async () => {
  const data = await request("GET", "/tutoring/api/tutorings");
  sessionsCache = data.data || [];
  if (role === "student") {
    renderList(getAvailableSessions());
    updateStudentSelectors();
  } else {
    renderList(data.data || []);
  }
};

const refreshTickets = async () => {
  const data = await request("GET", "/tutoring/api/tickets");
  const items = data.data || [];
  if (!items.length) {
    ticketList.innerHTML = "<div class='list-item'>No hay tickets emitidos.</div>";
    return;
  }
  ticketList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>Ticket #${item.id}</strong>
          <span>Sesion: ${item.session_id}</span>
          <span>${item.teacher} - ${item.date}</span>
          <span>Estudiante: ${item.student}</span>
        </div>
      `
    )
    .join("");
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    await refreshList();
    setStatus("Sesiones actualizadas.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("btn-ticket-refresh").addEventListener("click", async () => {
  try {
    await refreshTickets();
    setStatus("Tickets actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para obtener token.", true);
  rolePanel.innerHTML = "<p>Necesitas autenticarte para continuar.</p>";
} else {
  if (!email) {
    setStatus("No se encontro el correo del estudiante. Ingresa desde el portal.", true);
  }
  renderRolePanel();
  refreshList().catch((error) => setStatus(error.message, true));
  refreshTickets().catch((error) => setStatus(error.message, true));
}
