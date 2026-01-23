import "./style.css";

const API_GATEWAY = window.API_BASE_URL || "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Historial academico</h1>
        <p>Registro de cursos y calificaciones.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="/portal.html">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card" id="record-panel"></div>

      <div class="card">
        <h2>Registros</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="record-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="record-detail" class="list-item">Selecciona un registro.</div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para registrar calificaciones.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const recordList = document.getElementById("record-list");
const recordDetail = document.getElementById("record-detail");
const recordPanel = document.getElementById("record-panel");
let studentOptions = [];

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

const renderList = (items) => {
  if (!items.length) {
    recordList.innerHTML = "<div class='list-item'>No hay registros academicos.</div>";
    return;
  }
  recordList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.course}</strong>
          <span>Estudiante: ${item.student_email}</span>
          <span>Calificacion: ${item.grade}</span>
        </div>
      `
    )
    .join("");
  recordList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      const editable = role === "professor";
      recordDetail.innerHTML = `
        <strong>${item.course}</strong>
        <span>Estudiante: ${item.student_email}</span>
        <span>Calificacion: ${item.grade}</span>
        <span>ID: ${item.id}</span>
        ${
          editable
            ? `
          <div class="divider"></div>
          <label>Curso
            <input id="edit-course" value="${item.course}" />
          </label>
          <label>Calificacion
            <input id="edit-grade" type="number" step="0.1" min="0" max="20" value="${item.grade}" />
          </label>
          <div class="actions">
            <button class="btn btn-primary" id="btn-update-record">Actualizar</button>
            <button class="btn btn-outline" id="btn-delete-record">Eliminar</button>
          </div>
        `
            : ""
        }
      `;
      const updateButton = document.getElementById("btn-update-record");
      if (updateButton) {
        updateButton.addEventListener("click", async () => {
          const course = document.getElementById("edit-course").value.trim();
          const grade = Number(document.getElementById("edit-grade").value);
          if (course.length < 3 || Number.isNaN(grade)) {
            setStatus("Completa curso y calificacion.", true);
            return;
          }
          try {
            await request("PUT", `/records/api/records/${item.id}`, { course, grade });
            setStatus("Registro actualizado.");
            document.getElementById("btn-refresh").click();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
      const deleteButton = document.getElementById("btn-delete-record");
      if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
          try {
            await request("DELETE", `/records/api/records/${item.id}`);
            setStatus("Registro eliminado.");
            recordDetail.innerHTML = "Selecciona un registro.";
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
    const data = await request("GET", "/records/api/records");
    renderList(data.data || []);
    setStatus("Registros actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

const renderRecordPanel = () => {
  if (role !== "professor") {
    recordPanel.innerHTML = `
      <h2>Tu historial</h2>
      <p>Visualiza tus materias y notas registradas.</p>
      <div class="actions">
        <button class="btn btn-outline" id="btn-refresh-view">Actualizar</button>
      </div>
    `;
    document.getElementById("btn-refresh-view").addEventListener("click", async () => {
      try {
        const data = await request("GET", "/records/api/records");
        renderList(data.data || []);
        setStatus("Registros actualizados.");
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    return;
  }

  recordPanel.innerHTML = `
    <h2>Nuevo registro</h2>
    <form id="record-form">
      <label>Estudiante
        <select name="student_email" id="student-select" required></select>
      </label>
      <label>Curso
        <input name="course" placeholder="Programacion distribuida" required />
      </label>
      <label>Calificacion
        <input name="grade" type="number" step="0.1" min="0" max="20" placeholder="18.5" required />
      </label>
      <div class="actions">
        <button class="btn btn-primary" type="submit">Guardar</button>
      </div>
    </form>
  `;
  const studentSelect = document.getElementById("student-select");
  if (!studentOptions.length) {
    studentSelect.innerHTML = "<option value=''>Sin estudiantes registrados</option>";
  } else {
    studentSelect.innerHTML = `
      <option value="">Selecciona un estudiante</option>
      ${studentOptions
        .map((student) => `<option value="${student.email}">${student.full_name} (${student.email})</option>`)
        .join("")}
    `;
  }
  document.getElementById("record-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.grade = Number(payload.grade);
    try {
      await request("POST", "/records/api/records", payload);
      setStatus("Registro creado.");
      event.target.reset();
      const data = await request("GET", "/records/api/records");
      renderList(data.data || []);
    } catch (error) {
      setStatus(error.message, true);
    }
  });
};

if (!token) {
  setStatus("Inicia sesion en Auth para registrar calificaciones.", true);
} else {
  if (role === "professor") {
    request("GET", "/users/api/users/students")
      .then((data) => {
        studentOptions = data.data || [];
        renderRecordPanel();
        document.getElementById("btn-refresh").click();
      })
      .catch((error) => {
        setStatus(error.message, true);
        renderRecordPanel();
      });
  } else {
    renderRecordPanel();
    document.getElementById("btn-refresh").click();
  }
}
