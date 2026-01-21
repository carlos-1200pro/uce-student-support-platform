import "./style.css";

const API_GATEWAY = "http://localhost:8080";
const app = document.getElementById("app");

const params = new URLSearchParams(window.location.search);
if (params.get("token")) {
  localStorage.setItem("auth_token", params.get("token"));
  localStorage.setItem("auth_role", params.get("role") || "student");
  localStorage.setItem("auth_name", params.get("name") || "");
  localStorage.setItem("auth_email", params.get("email") || "");
  window.history.replaceState({}, "", window.location.pathname);
}

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Foro estudiantil</h1>
        <p>Comparte temas, ideas y preguntas con la comunidad.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="http://localhost:3001">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Nuevo tema</h2>
        <form id="post-form">
          <label>Titulo
            <input name="title" placeholder="Tema de debate" required />
          </label>
          <label>Autor
            <input name="author" placeholder="Nombre completo" required />
          </label>
          <label>Contenido
            <textarea name="content" placeholder="Escribe tu mensaje..." required></textarea>
          </label>
          <div class="actions">
            <button class="btn btn-primary" type="submit">Publicar</button>
          </div>
        </form>
      </div>

      <div class="card">
        <h2>Temas recientes</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="post-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="post-detail" class="list-item">Selecciona un tema.</div>
        <form id="comment-form">
          <label>Autor
            <input name="author" placeholder="Tu nombre" required />
          </label>
          <label>Comentario
            <textarea name="content" placeholder="Escribe tu comentario..." required></textarea>
          </label>
          <div class="actions">
            <button class="btn btn-primary" type="submit" id="btn-comment" disabled>Comentar</button>
          </div>
        </form>
        <div id="comment-list" class="list"></div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para publicar en el foro.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const postList = document.getElementById("post-list");
const postDetail = document.getElementById("post-detail");
const commentList = document.getElementById("comment-list");
const commentForm = document.getElementById("comment-form");
const commentButton = document.getElementById("btn-comment");
let selectedPostId = null;
let selectedPost = null;

const token = localStorage.getItem("auth_token");
const role = localStorage.getItem("auth_role") || "invitado";
const displayName = localStorage.getItem("auth_name") || localStorage.getItem("auth_email") || "";
rolePill.textContent = `Rol: ${role}`;

const postAuthorInput = document.querySelector("input[name='author']");
const commentAuthorInput = commentForm.querySelector("input[name='author']");
if (displayName) {
  postAuthorInput.value = displayName;
  postAuthorInput.readOnly = true;
  commentAuthorInput.value = displayName;
  commentAuthorInput.readOnly = true;
}

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

const renderPostDetail = (item) => {
  const canEdit = displayName && item.author === displayName;
  return `
    <strong>${item.title}</strong>
    <span>Autor: ${item.author}</span>
    <span>${item.content}</span>
    ${canEdit ? `
      <div class="divider"></div>
      <label>Editar titulo
        <input id="edit-title" value="${item.title}" />
      </label>
      <label>Editar contenido
        <textarea id="edit-content">${item.content}</textarea>
      </label>
      <div class="actions">
        <button class="btn btn-primary" id="btn-update-post">Actualizar</button>
        <button class="btn btn-outline" id="btn-delete-post">Eliminar</button>
      </div>
    ` : ""}
  `;
};

const renderList = (items) => {
  if (!items.length) {
    postList.innerHTML = "<div class='list-item'>No hay temas publicados.</div>";
    return;
  }
  postList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.title}</strong>
          <span>Autor: ${item.author}</span>
          <span>${item.content}</span>
        </div>
      `
    )
    .join("");
  postList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      selectedPostId = item.id;
      selectedPost = item;
      commentButton.disabled = false;
      postDetail.innerHTML = renderPostDetail(item);
      const updateButton = document.getElementById("btn-update-post");
      if (updateButton) {
        updateButton.addEventListener("click", async () => {
          const title = document.getElementById("edit-title").value.trim();
          const content = document.getElementById("edit-content").value.trim();
          if (title.length < 3 || content.length < 1) {
            setStatus("Completa titulo y contenido.", true);
            return;
          }
          try {
            await request("PUT", `/forum/api/posts/${item.id}`, { title, content });
            setStatus("Tema actualizado.");
            document.getElementById("btn-refresh").click();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
      const deleteButton = document.getElementById("btn-delete-post");
      if (deleteButton) {
        deleteButton.addEventListener("click", async () => {
          try {
            await request("DELETE", `/forum/api/posts/${item.id}`);
            setStatus("Tema eliminado.");
            selectedPostId = null;
            selectedPost = null;
            commentButton.disabled = true;
            postDetail.innerHTML = "Selecciona un tema.";
            commentList.innerHTML = "";
            document.getElementById("btn-refresh").click();
          } catch (error) {
            setStatus(error.message, true);
          }
        });
      }
      loadComments();
    });
  });
};

const loadComments = async () => {
  if (!selectedPostId) return;
  const data = await request("GET", `/forum/api/posts/${selectedPostId}/comments`);
  const items = data.data || [];
  if (!items.length) {
    commentList.innerHTML = "<div class='list-item'>Sin comentarios.</div>";
    return;
  }
  commentList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>${item.author}</strong>
          <span>${item.content}</span>
        </div>
      `
    )
    .join("");
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    const data = await request("GET", "/forum/api/posts");
    renderList(data.data || []);
    setStatus("Temas actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

document.getElementById("post-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  try {
    await request("POST", "/forum/api/posts", payload);
    setStatus("Tema publicado.");
    event.target.reset();
    const data = await request("GET", "/forum/api/posts");
    renderList(data.data || []);
  } catch (error) {
    setStatus(error.message, true);
  }
});

commentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedPostId) {
    setStatus("Selecciona un tema para comentar.", true);
    return;
  }
  const payload = Object.fromEntries(new FormData(event.target).entries());
  if (!payload.author || !payload.content) {
    setStatus("Completa autor y comentario.", true);
    return;
  }
  try {
    await request("POST", `/forum/api/posts/${selectedPostId}/comments`, payload);
    setStatus("Comentario publicado.");
    event.target.reset();
    if (displayName) {
      commentAuthorInput.value = displayName;
    }
    await loadComments();
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para publicar.", true);
} else {
  document.getElementById("btn-refresh").click();
}
