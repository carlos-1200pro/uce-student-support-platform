import "./style.css";

const API_GATEWAY = "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Usuarios</h1>
        <p>Gestion de perfiles vinculados al sistema académico.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="http://localhost:3001">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Crear usuario</h2>
        <form id="user-form">
          <label>Nombre completo
            <input name="name" placeholder="Carlos Andrade" required />
          </label>
          <label>Correo institucional
            <input name="email" type="email" placeholder="carlos@uce.edu.ec" required />
          </label>
          <div class="actions">
            <button class="btn btn-primary" type="submit">Guardar</button>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Listado de usuarios</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="user-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="user-detail" class="list-item">Selecciona un usuario.</div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para gestionar usuarios.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const userList = document.getElementById("user-list");
const userDetail = document.getElementById("user-detail");

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
    userList.innerHTML = "<div class='list-item'>Sin usuarios registrados.</div>";
    return;
  }
  userList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.name}</strong>
          <span>${item.email}</span>
        </div>
      `
    )
    .join("");
  userList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      userDetail.innerHTML = `
        <strong>${item.name}</strong>
        <span>${item.email}</span>
        <span>ID: ${item.id}</span>
      `;
    });
  });
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    const data = await request("GET", "/users/api/users");
    renderList(data.data || []);
    setStatus("Usuarios actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());
  try {
    await request("POST", "/users/api/users", payload);
    setStatus("Usuario registrado correctamente.");
    event.target.reset();
    const data = await request("GET", "/users/api/users");
    renderList(data.data || []);
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para obtener token.", true);
} else {
  document.getElementById("btn-refresh").click();
}
