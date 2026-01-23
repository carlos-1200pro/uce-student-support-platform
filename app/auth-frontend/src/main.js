import "./style.css";

const API_GATEWAY = window.API_BASE_URL || "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <main>
    <div class="shell">
      <section class="hero">
        <h1>Hola, UCE</h1>
        <p>Accede a tutorias, foros y horarios desde un portal unico. Docentes crean horarios, estudiantes reservan sesiones.</p>
        <ul>
          <li><span>01</span>Acceso por rol (estudiante / profesor)</li>
          <li><span>02</span>Sesiones de tutoria con disponibilidad real</li>
          <li><span>03</span>Notificaciones y pagos simulados</li>
        </ul>
      </section>
      <section class="panel">
        <div class="tabs">
          <button id="tab-login" class="active">Iniciar sesion</button>
          <button id="tab-register">Crear cuenta</button>
        </div>
        <div id="form-area"></div>
        <div id="status" class="status">Usa tu correo institucional para entrar.</div>
        <div class="footer">Gateway: ${API_GATEWAY}</div>
      </section>
    </div>
  </main>
`;

const formArea = document.getElementById("form-area");
const statusEl = document.getElementById("status");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

const setStatus = (message, tone = "info") => {
  statusEl.textContent = message;
  if (tone === "error") {
    statusEl.style.background = "#ffe7e7";
    statusEl.style.color = "#7a1e1e";
    return;
  }
  statusEl.style.background = "var(--accent-soft)";
  statusEl.style.color = "var(--accent-deep)";
};


const renderLogin = () => {
  formArea.innerHTML = `
    <form id="login-form" class="form-block">
      <label>
        Correo institucional
        <input type="email" name="email" placeholder="nombre@uce.edu.ec" required />
      </label>
      <label>
        Contrasena
        <input type="password" name="password" placeholder="********" required />
      </label>
      <div class="actions">
        <button class="primary" type="submit">Ingresar</button>
      </div>
    </form>
  `;

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const payload = Object.fromEntries(formData.entries());
    setStatus("Validando credenciales...");
    try {
      const response = await apiRequest("/auth/api/login", payload);
      localStorage.setItem("auth_token", response.data.token);
      localStorage.setItem("auth_role", response.data.role);
      localStorage.setItem("auth_name", response.data.full_name || "");
      localStorage.setItem("auth_email", response.data.email || "");
      setStatus(`Bienvenido ${response.data.full_name} (${response.data.role}).`, "info");
      const token = response.data.token;
      const role = response.data.role;
      const name = response.data.full_name || "";
      const email = response.data.email || "";
      window.location.href = `/portal.html?token=${token}&role=${role}&name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}`;
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
};

const renderRegister = () => {
  formArea.innerHTML = `
    <form id="register-form" class="form-block">
      <div class="inline">
        <label>
          Nombre completo
          <input type="text" name="full_name" placeholder="Maria Perez" required />
        </label>
        <label>
          Rol
          <select name="role" required>
            <option value="student">Estudiante</option>
            <option value="professor">Profesor</option>
          </select>
        </label>
      </div>
      <label>
        Correo institucional
        <input type="email" name="email" placeholder="maria@uce.edu.ec" required />
      </label>
      <label>
        Contrasena
        <input type="password" name="password" placeholder="Minimo 4 caracteres" required />
      </label>
      <div class="actions">
        <button class="primary" type="submit">Crear cuenta</button>
        <button class="ghost" type="button" id="btn-reset">Limpiar</button>
      </div>
    </form>
  `;

  document.getElementById("btn-reset").addEventListener("click", () => {
    document.getElementById("register-form").reset();
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const payload = Object.fromEntries(formData.entries());
    setStatus("Registrando usuario...");
    try {
      const response = await apiRequest("/auth/api/register", payload);
      setStatus(`Cuenta creada para ${response.data.email}.`, "info");
      tabLogin.click();
    } catch (error) {
      setStatus(error.message, "error");
    }
  });
};


const apiRequest = async (path, body) => {
  const response = await fetch(`${API_GATEWAY}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok || !data.success) {
    throw new Error(data.message || "Error en la solicitud");
  }
  return data;
};

tabLogin.addEventListener("click", () => {
  tabLogin.classList.add("active");
  tabRegister.classList.remove("active");
  renderLogin();
});

tabRegister.addEventListener("click", () => {
  tabRegister.classList.add("active");
  tabLogin.classList.remove("active");
  renderRegister();
});

const token = localStorage.getItem("auth_token");
if (token && !window.location.pathname.endsWith("portal.html")) {
  const role = localStorage.getItem("auth_role") || "student";
  const name = localStorage.getItem("auth_name") || "";
  const email = localStorage.getItem("auth_email") || "";
  window.location.href = `/portal.html?token=${token}&role=${role}&name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}`;
} else {
  renderLogin();
}
