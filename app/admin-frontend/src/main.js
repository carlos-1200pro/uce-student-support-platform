import "./style.css";

const API_GATEWAY = "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Panel administrador</h1>
        <p>Monitorea servicios y registra auditorias del sistema.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="http://localhost:3001">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Estado del gateway</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-health">Ver estado</button>
        </div>
        <div id="health-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Registrar auditoria</h2>
        <form id="audit-form">
          <label>Accion
            <input name="action" placeholder="LOGIN" required />
          </label>
          <label>Actor
            <input name="actor" placeholder="admin@uce.edu.ec" required />
          </label>
          <div class="actions">
            <button class="btn btn-primary" type="submit">Guardar</button>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Auditorias</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="audit-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="audit-detail" class="list-item">Selecciona una auditoria.</div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para acceder a auditoria.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const auditList = document.getElementById("audit-list");
const healthList = document.getElementById("health-list");
const auditDetail = document.getElementById("audit-detail");

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

const request = async (method, path, body, useAuth = true) => {
  const headers = { "Content-Type": "application/json" };
  if (useAuth && token) headers.Authorization = `Bearer ${token}`;
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

const renderAuditList = (items) => {
  if (!items.length) {
    auditList.innerHTML = "<div class='list-item'>Sin auditorias registradas.</div>";
    return;
  }
  auditList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.action}</strong>
          <span>Actor: ${item.actor}</span>
        </div>
      `
    )
    .join("");
  auditList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      auditDetail.innerHTML = `
        <strong>${item.action}</strong>
        <span>Actor: ${item.actor}</span>
        <span>ID: ${item.id}</span>
      `;
    });
  });
};

const renderHealth = (health) => {
  healthList.innerHTML = `
    <div class="list-item">
      <strong>Estado: ${health.status}</strong>
      <span>Servicio: ${health.service}</span>
      <span>Upstreams: ${health.upstreams.join(", ")}</span>
    </div>
  `;
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    const data = await request("GET", "/audit/api/audits");
    renderAuditList(data.data || []);
    setStatus("Auditorias actualizadas.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("btn-health").addEventListener("click", async () => {
  try {
    const res = await fetch(`${API_GATEWAY}/health`);
    const data = await res.json();
    renderHealth(data);
    setStatus("Gateway en linea.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("audit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  try {
    await request("POST", "/audit/api/audits", payload);
    setStatus("Auditoria registrada.");
    event.target.reset();
    const data = await request("GET", "/audit/api/audits");
    renderAuditList(data.data || []);
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para acceder al panel.", true);
} else {
  document.getElementById("btn-refresh").click();
}
