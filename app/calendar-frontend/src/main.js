import "./style.css";

const API_GATEWAY = window.API_BASE_URL || "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Calendario</h1>
        <p>Eventos academicos, horarios y actividades relevantes.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="/portal.html">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Nuevo evento</h2>
        <form id="event-form">
          <label>Titulo
            <input name="title" placeholder="Clase magistral" required />
          </label>
          <label>Fecha
            <input name="date" type="datetime-local" required />
          </label>
          <label>Ubicacion
            <input name="location" placeholder="Auditorio principal" required />
          </label>
          <div class="actions">
            <button class="btn btn-primary" type="submit">Crear</button>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Eventos programados</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="event-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="event-detail" class="list-item">Selecciona un evento.</div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para gestionar eventos.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const eventList = document.getElementById("event-list");
const eventDetail = document.getElementById("event-detail");
const eventForm = document.getElementById("event-form");

const params = new URLSearchParams(window.location.search);
if (params.get("token")) {
  localStorage.setItem("auth_token", params.get("token"));
  localStorage.setItem("auth_role", params.get("role") || "student");
  localStorage.setItem("auth_name", params.get("name") || "");
  localStorage.setItem("auth_email", params.get("email") || "");
  window.history.replaceState({}, "", window.location.pathname);
}

const token = localStorage.getItem("auth_token");
const role = localStorage.getItem("auth_role") || "invitado";
const email = localStorage.getItem("auth_email") || "";
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

const canEditEvent = (item) => {
  if (role === "professor") return true;
  if (role === "student") return item.student_email === email;
  return false;
};

const toDateInputValue = (value) => {
  if (!value) return "";
  if (value.includes("T")) return value;
  return value.replace(" ", "T");
};

const renderList = (items) => {
  if (!items.length) {
    eventList.innerHTML = "<div class='list-item'>No hay eventos registrados.</div>";
    return;
  }
  eventList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.title}</strong>
          <span>Estudiante: ${item.student_email}</span>
          <span>Fecha: ${item.date}</span>
          <span>Ubicacion: ${item.location}</span>
        </div>
      `
    )
    .join("");
  eventList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      const editable = canEditEvent(item);
      eventDetail.innerHTML = `
        <strong>${item.title}</strong>
        <span>Estudiante: ${item.student_email}</span>
        <span>${item.date}</span>
        <span>${item.location}</span>
        ${
          editable
            ? `
          <div class="divider"></div>
          <label>Titulo
            <input id="edit-title" value="${item.title}" />
          </label>
          <label>Fecha
            <input id="edit-date" type="datetime-local" value="${toDateInputValue(item.date)}" />
          </label>
          <label>Ubicacion
            <input id="edit-location" value="${item.location}" />
          </label>
          <div class="actions">
            <button class="btn btn-primary" id="btn-update-event">Actualizar</button>
            <button class="btn btn-outline" id="btn-delete-event">Eliminar</button>
          </div>
        `
            : ""
        }
      `;
      const updateButton = document.getElementById("btn-update-event");
      if (updateButton) {
        updateButton.addEventListener("click", async () => {
          const title = document.getElementById("edit-title").value.trim();
          const date = document.getElementById("edit-date").value;
          const location = document.getElementById("edit-location").value.trim();
          if (title.length < 3 || location.length < 3 || !date) {
            setStatus("Completa titulo, fecha y ubicacion.", true);
            return;
          }
          try {
            await request("PUT", `/calendar/api/events/${item.id}`, { title, date, location });
            setStatus("Evento actualizado.");
            document.getElementById("btn-refresh").click();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
      const deleteButton = document.getElementById("btn-delete-event");
      if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
          try {
            await request("DELETE", `/calendar/api/events/${item.id}`);
            setStatus("Evento eliminado.");
            eventDetail.innerHTML = "Selecciona un evento.";
            document.getElementById("btn-refresh").click();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
    });
  });
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    const data = await request("GET", "/calendar/api/events");
    renderList(data.data || []);
    setStatus("Eventos actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

const dateInput = eventForm.querySelector("input[name='date']");
const now = new Date();
const pad = (value) => String(value).padStart(2, "0");
dateInput.min = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(
  now.getHours()
)}:${pad(now.getMinutes())}`;

eventForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  if (!payload.title || payload.title.length < 3) {
    setStatus("El titulo debe tener al menos 3 caracteres.", true);
    return;
  }
  if (!payload.location || payload.location.length < 3) {
    setStatus("La ubicacion debe tener al menos 3 caracteres.", true);
    return;
  }
  if (!payload.date) {
    setStatus("Selecciona fecha y hora.", true);
    return;
  }
  try {
    await request("POST", "/calendar/api/events", payload);
    setStatus("Evento creado.");
    event.target.reset();
    const data = await request("GET", "/calendar/api/events");
    renderList(data.data || []);
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para gestionar eventos.", true);
} else {
  document.getElementById("btn-refresh").click();
}
