import "./portal.css";

const portal = document.getElementById("portal");

const params = new URLSearchParams(window.location.search);
if (params.get("token")) {
  localStorage.setItem("auth_token", params.get("token"));
  localStorage.setItem("auth_role", params.get("role") || "student");
  localStorage.setItem("auth_name", params.get("name") || "");
  localStorage.setItem("auth_email", params.get("email") || "");
  window.history.replaceState({}, "", window.location.pathname);
}

const token = localStorage.getItem("auth_token");
const role = localStorage.getItem("auth_role") || "student";
const name = localStorage.getItem("auth_name") || "usuario";
const email = localStorage.getItem("auth_email") || "";

if (!token) {
  window.location.href = "/";
}

const modules = [
  {
    id: "users",
    title: "Usuarios",
    desc: "Gestiona perfiles y datos basicos.",
    url: `${window.location.origin}/users/`,
    roles: ["admin"],
  },
  {
    id: "tutoring",
    title: "Tutorias",
    desc: "Docentes publican horarios, estudiantes reservan.",
    url: `${window.location.origin}/tutoring/`,
    roles: ["student", "professor"],
  },
  {
    id: "forum",
    title: "Foro",
    desc: "Comparte temas y comentarios con la comunidad.",
    url: `${window.location.origin}/forum/`,
    roles: ["student", "professor"],
  },
  {
    id: "payment",
    title: "Pagos",
    desc: "Ordenes por materias y pago en linea simulado.",
    url: `${window.location.origin}/payments/`,
    roles: ["student", "professor"],
  },
  {
    id: "calendar",
    title: "Calendario",
    desc: "Eventos academicos e historial de horarios.",
    url: `${window.location.origin}/calendar/`,
    roles: ["student", "professor"],
  },
  {
    id: "records",
    title: "Historial academico",
    desc: "Calificaciones y registros del estudiante.",
    url: `${window.location.origin}/records/`,
    roles: ["student", "professor"],
  },
  {
    id: "admin",
    title: "Administracion",
    desc: "Auditoria y estado de servicios.",
    url: `${window.location.origin}/admin/`,
    roles: ["admin"],
  },
];

const withAuth = (baseUrl) => {
  const query = new URLSearchParams({
    token,
    role,
    name,
    email,
  }).toString();
  return `${baseUrl}?${query}`;
};

portal.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Portal UCE</h1>
        <p>Hola ${name}. Selecciona el modulo para continuar.</p>
      </div>
      <div class="actions">
        <div class="pill">Rol: ${role}</div>
        <button class="btn btn-outline" id="btn-logout">Salir</button>
      </div>
    </header>

    <section class="grid">
      ${modules
        .filter((mod) => mod.roles.includes(role))
        .map(
          (mod) => `
            <div class="card" data-id="${mod.id}">
              <h3>${mod.title}</h3>
              <p>${mod.desc}</p>
              <a class="btn btn-primary" href="${withAuth(mod.url)}">Ingresar</a>
            </div>
          `
        )
        .join("")}
    </section>

    <div class="status">Sesion activa: ${email || "sin correo"}.</div>
  </div>
`;

document.getElementById("btn-logout").addEventListener("click", () => {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_role");
  localStorage.removeItem("auth_name");
  localStorage.removeItem("auth_email");
  window.location.href = "/";
});
