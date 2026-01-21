import "./style.css";

const API_GATEWAY = "http://localhost:8080";
const app = document.getElementById("app");

app.innerHTML = `
  <div class="page">
    <header class="topbar">
      <div>
        <h1>Pagos en linea</h1>
        <p>Genera ordenes de cobro y simula pagos con PayPal.</p>
      </div>
      <div class="actions">
        <a class="btn btn-outline" href="http://localhost:3001">Volver al portal</a>
        <div class="pill" id="role-pill">Rol: invitado</div>
      </div>
    </header>

    <section class="checkout">
      <div class="card summary" id="summary-panel"></div>

      <div class="card payment" id="payment-panel"></div>
    </section>

    <section class="grid" id="history-section">
      <div class="card">
        <h2>Pagos registrados</h2>
        <div class="actions">
          <button class="btn btn-outline" id="btn-refresh">Actualizar</button>
        </div>
        <div id="payment-list" class="list"></div>
      </div>

      <div class="card">
        <h2>Detalle</h2>
        <div id="payment-detail" class="list-item">Selecciona un pago.</div>
      </div>
    </section>

    <div class="status" id="status">Inicia sesion para gestionar pagos.</div>
  </div>
`;

const statusEl = document.getElementById("status");
const rolePill = document.getElementById("role-pill");
const paymentList = document.getElementById("payment-list");
const paymentDetail = document.getElementById("payment-detail");
const summaryPanel = document.getElementById("summary-panel");
const paymentPanel = document.getElementById("payment-panel");
const historySection = document.getElementById("history-section");
let currentOrder = null;
const requiredCourses = [
  "Programacion distribuida",
  "Arquitectura de software",
  "Mineria de datos",
  "Control de seguridad",
  "Investigacion operativa",
];

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

const canDeletePayment = (item) => {
  if (role === "professor") return true;
  if (role === "student") return item.status !== "PAID";
  return false;
};

const canEditPayment = (item) => {
  if (role === "professor") return true;
  if (role === "student") return item.status !== "PAID";
  return false;
};

const renderList = (items) => {
  if (!items.length) {
    paymentList.innerHTML = "<div class='list-item'>No hay pagos registrados.</div>";
    return;
  }
  paymentList.innerHTML = items
    .map(
      (item) => `
        <div class="list-item">
          <strong>Pago #${item.id}</strong>
          ${item.student_email ? `<span>Estudiante: ${item.student_email}</span>` : ""}
          <span>Monto: ${item.amount} ${item.currency}</span>
          <span>Estado: ${item.status}</span>
          ${canDeletePayment(item) ? `<div class="actions"><button class="btn btn-outline btn-delete-payment" data-id="${item.id}">Eliminar</button></div>` : ""}
        </div>
      `
    )
    .join("");
  paymentList.querySelectorAll(".list-item").forEach((node, index) => {
    node.addEventListener("click", () => {
      const item = items[index];
      paymentDetail.innerHTML = renderPaymentDetail(item);
      if (canEditPayment(item)) {
        const updateButton = document.getElementById("btn-update-payment");
        if (updateButton) {
          updateButton.addEventListener("click", async () => {
            const amount = Number(document.getElementById("edit-amount").value);
            const status = document.getElementById("edit-status").value;
            try {
              await request("PUT", `/payment/api/payments/${item.id}`, { amount, status });
              setStatus("Pago actualizado.");
              document.getElementById("btn-refresh").click();
            } catch (error) {
              setStatus(error.message, true);
            }
          });
        }
        const deleteButton = document.getElementById("btn-delete-payment");
        if (deleteButton) {
          deleteButton.addEventListener("click", async () => {
            try {
              await request("DELETE", `/payment/api/payments/${item.id}`);
              setStatus("Pago eliminado.");
              document.getElementById("btn-refresh").click();
            } catch (error) {
              setStatus(error.message, true);
            }
          });
        }
      }
    });
  });
  paymentList.querySelectorAll(".btn-delete-payment").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const paymentId = Number(button.dataset.id);
      try {
        await request("DELETE", `/payment/api/payments/${paymentId}`);
        setStatus("Pago eliminado.");
        document.getElementById("btn-refresh").click();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
  });
};

const renderPaymentDetail = (item) => {
  if (!canEditPayment(item)) {
    return `
      <strong>Pago #${item.id}</strong>
      ${item.student_email ? `<span>Estudiante: ${item.student_email}</span>` : ""}
      <span>${item.amount} ${item.currency}</span>
      <span>Estado: ${item.status}</span>
    `;
  }
  const statusOptions =
    role === "professor"
      ? `
        <option value="PENDING" ${item.status === "PENDING" ? "selected" : ""}>PENDING</option>
        <option value="PAID" ${item.status === "PAID" ? "selected" : ""}>PAID</option>
        <option value="CANCELLED" ${item.status === "CANCELLED" ? "selected" : ""}>CANCELLED</option>
      `
      : `
        <option value="PENDING" ${item.status === "PENDING" ? "selected" : ""}>PENDING</option>
        <option value="CANCELLED" ${item.status === "CANCELLED" ? "selected" : ""}>CANCELLED</option>
      `;
  return `
    <strong>Pago #${item.id}</strong>
    ${item.student_email ? `<span>Estudiante: ${item.student_email}</span>` : ""}
    <label>Monto
      <input id="edit-amount" type="number" step="0.01" value="${item.amount}" />
    </label>
    <label>Estado
      <select id="edit-status">
        ${statusOptions}
      </select>
    </label>
    <div class="actions">
      <button class="btn btn-primary" id="btn-update-payment">Actualizar</button>
      ${canDeletePayment(item) ? `<button class="btn btn-outline" id="btn-delete-payment">Eliminar</button>` : ""}
    </div>
  `;
};

const renderFees = (items) => {
  if (!items.length) {
    return "<div class='list-item'>No hay materias configuradas.</div>";
  }
  return items
    .map(
      (item) => `
        <label class="fee-row">
          <input type="checkbox" value="${item.id}" />
          <span>${item.course}</span>
          <span class="fee-amount">$${item.amount}</span>
        </label>
      `
    )
    .join("");
};

const normalizeFees = (fees) => {
  const map = new Map();
  fees.forEach((fee) => {
    const key = fee.course.trim().toLowerCase();
    if (!map.has(key)) {
      map.set(key, fee);
    }
  });
  const ordered = [];
  requiredCourses.forEach((course) => {
    const key = course.toLowerCase();
    if (map.has(key)) {
      ordered.push(map.get(key));
      map.delete(key);
    }
  });
  const rest = Array.from(map.values()).sort((a, b) => a.course.localeCompare(b.course));
  return [...ordered, ...rest];
};

const loadFees = async () => {
  const data = await request("GET", "/payment/api/fees");
  return data.data || [];
};

const renderPanels = async () => {
  const fees = await loadFees();
  if (role === "professor") {
    const feeRows = fees
      .map(
        (fee) => `
        <div class="fee-admin" data-id="${fee.id}">
          <input name="course" value="${fee.course}" />
          <input name="amount" type="number" step="0.01" value="${fee.amount}" />
          <button class="btn btn-outline btn-save" type="button">Actualizar</button>
          <button class="btn btn-danger btn-delete" type="button">Eliminar</button>
        </div>
      `
      )
      .join("");
    summaryPanel.innerHTML = `
      <h2>Configurar valores</h2>
      <form id="fee-form">
        <label>Materia
          <input name="course" placeholder="Programacion distribuida" required />
        </label>
        <label>Valor
          <input name="amount" type="number" step="0.01" placeholder="120.00" required />
        </label>
        <div class="actions">
          <button class="btn btn-primary" type="submit">Guardar</button>
        </div>
      </form>
      <div class="list">
        ${feeRows || "<div class='list-item'>No hay materias configuradas.</div>"}
      </div>
    `;
    document.getElementById("fee-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(event.target).entries());
      payload.amount = Number(payload.amount);
      try {
        await request("POST", "/payment/api/fees", payload);
        setStatus("Materia registrada.");
        await renderPanels();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    document.querySelectorAll(".fee-admin").forEach((row) => {
      const feeId = Number(row.dataset.id);
      const courseInput = row.querySelector("input[name='course']");
      const amountInput = row.querySelector("input[name='amount']");
      row.querySelector(".btn-save").addEventListener("click", async () => {
        try {
          const payload = {
            course: courseInput.value.trim(),
            amount: Number(amountInput.value),
          };
          await request("PUT", `/payment/api/fees/${feeId}`, payload);
          setStatus("Materia actualizada.");
          await renderPanels();
        } catch (error) {
          setStatus(error.message, true);
        }
      });
      row.querySelector(".btn-delete").addEventListener("click", async () => {
        try {
          await request("DELETE", `/payment/api/fees/${feeId}`);
          setStatus("Materia eliminada.");
          await renderPanels();
        } catch (error) {
          setStatus(error.message, true);
        }
      });
    });
    paymentPanel.innerHTML = `
      <h2>Pago en linea</h2>
      <div class="empty-state">
        Genera una orden como estudiante para habilitar el pago.
      </div>
    `;
    historySection.style.display = "grid";
  } else {
    const displayFees = normalizeFees(fees);
    const missing = requiredCourses.filter(
      (course) => !displayFees.some((fee) => fee.course.trim().toLowerCase() === course.toLowerCase())
    );
    summaryPanel.innerHTML = `
      <div class="summary-header">
        <div>
          <h2>Resumen del pedido</h2>
          <p>Selecciona materias y genera la orden de pago.</p>
        </div>
        <span class="brand">PayPal</span>
      </div>
      <div class="summary-box">
        <div class="summary-line">
          <span>Mi carrito</span>
          <strong id="summary-total">$0.00</strong>
        </div>
        <div class="summary-line">
          <span>Envio</span>
          <span>$0.00</span>
        </div>
        <div class="summary-line total">
          <span>Total</span>
          <strong id="summary-grand">$0.00</strong>
        </div>
      </div>
      <div class="summary-items" id="summary-items">Selecciona materias.</div>
      ${missing.length ? `<div class="list-item warning">Faltan materias: ${missing.join(", ")}.</div>` : ""}
      <form id="order-form">
        <div class="list">${renderFees(displayFees)}</div>
        <div class="actions">
          <button class="btn btn-primary" type="submit">Generar orden</button>
        </div>
      </form>
    `;
    const summaryTotal = document.getElementById("summary-total");
    const summaryGrand = document.getElementById("summary-grand");
    const summaryItems = document.getElementById("summary-items");
    const checkboxes = Array.from(document.querySelectorAll("input[type='checkbox']"));
    const updateTotal = () => {
      const selectedIds = checkboxes.filter((c) => c.checked).map((c) => Number(c.value));
      const selectedItems = displayFees.filter((f) => selectedIds.includes(f.id));
      const total = selectedItems
        .filter((f) => selectedIds.includes(f.id))
        .reduce((acc, f) => acc + Number(f.amount), 0);
      summaryTotal.textContent = `$${total.toFixed(2)}`;
      summaryGrand.textContent = `$${total.toFixed(2)}`;
      if (!selectedItems.length) {
        summaryItems.textContent = "Selecciona materias.";
        return;
      }
      summaryItems.innerHTML = selectedItems
        .map(
          (item) => `
          <div class="summary-item">
            <span>${item.course}</span>
            <strong>$${item.amount}</strong>
          </div>
        `
        )
        .join("");
    };
    checkboxes.forEach((c) => c.addEventListener("change", updateTotal));
    document.getElementById("order-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const selected = Array.from(event.target.querySelectorAll("input[type='checkbox']:checked")).map(
        (input) => Number(input.value)
      );
      if (!selected.length) {
        setStatus("Selecciona al menos una materia.", true);
        return;
      }
      try {
        const order = await request("POST", "/payment/api/orders", { courses: selected });
        setStatus("Orden generada.");
        currentOrder = order.data;
        renderPaymentForm(order.data);
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    paymentPanel.innerHTML = `
      <div class="payment-header">
        <div>
          <h2>Pago seguro</h2>
          <p>Completa la informacion para pagar con tarjeta.</p>
        </div>
        <span class="brand">Secure</span>
      </div>
      <div class="empty-state">
        Genera una orden para habilitar el formulario de pago.
      </div>
    `;
    historySection.style.display = "grid";
  }
};

const renderPaymentForm = (order) => {
  paymentPanel.innerHTML = `
    <div class="payment-header">
      <div>
        <h2>Pago seguro</h2>
        <p>Procesamos tu pago en linea con datos enmascarados.</p>
      </div>
      <span class="brand">PayPal</span>
    </div>
    <div class="method-tabs">
      <button class="method-btn active" type="button">Tarjeta</button>
      <button class="method-btn" type="button" disabled>PayPal</button>
    </div>
    <div class="order-chip">Orden #${order.payment_id} · Total $${order.total}</div>
    <form id="pay-form" class="payment-form">
      <label>Correo electronico
        <input name="email" type="email" placeholder="correo@uce.edu.ec" required />
      </label>
      <label>Numero de tarjeta
        <input name="card_number" inputmode="numeric" placeholder="1234 1234 1234 1234" required />
      </label>
      <div class="split">
        <label>Vencimiento
          <input name="expiry" placeholder="MM/AA" required />
        </label>
        <label>CVV
          <input name="cvv" inputmode="numeric" placeholder="123" required />
        </label>
      </div>
      <label>Nombre en la tarjeta
        <input name="cardholder" placeholder="Nombre Apellido" required />
      </label>
      <label>Pais o region
        <select name="country" required>
          <option value="EC">Ecuador</option>
          <option value="CO">Colombia</option>
          <option value="PE">Peru</option>
          <option value="MX">Mexico</option>
        </select>
      </label>
      <label>Codigo postal
        <input name="postal" placeholder="170000" required />
      </label>
      <div class="actions">
        <button class="btn btn-primary" type="submit">Pagar $${order.total}</button>
      </div>
    </form>
    <div id="receipt"></div>
  `;
  paymentDetail.innerHTML = `
    <strong>Orden #${order.payment_id}</strong>
    <span>Total: $${order.total}</span>
    <span>Materias: ${order.items.map((i) => i.course).join(", ")}</span>
    <span>Estado: pendiente de pago</span>
  `;
  document.getElementById("pay-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = Object.fromEntries(new FormData(event.target).entries());
    const digits = String(formData.card_number || "").replace(/\D/g, "");
    if (digits.length < 4) {
      setStatus("El numero de tarjeta debe tener al menos 4 digitos.", true);
      return;
    }
    const payload = {
      method: "CARD",
      cardholder: formData.cardholder,
      expiry: formData.expiry,
      card_last4: digits.slice(-4),
    };
    try {
      const receipt = await request("POST", `/payment/api/payments/${order.payment_id}/pay`, payload);
      document.getElementById("receipt").innerHTML = `
        <div class="list-item">
          <strong>Comprobante</strong>
          <span>Orden: #${order.payment_id}</span>
          <span>Pago #${receipt.data.payment_id}</span>
          <span>Metodo: ${receipt.data.method}</span>
          <span>Tarjeta: **** ${receipt.data.card_last4}</span>
          <span>Fecha: ${receipt.data.paid_at}</span>
        </div>
      `;
      paymentDetail.innerHTML = `
        <strong>Comprobante</strong>
        <span>Orden: #${order.payment_id}</span>
        <span>Pago: #${receipt.data.payment_id}</span>
        <span>Metodo: ${receipt.data.method}</span>
        <span>Tarjeta: **** ${receipt.data.card_last4}</span>
        <span>Fecha: ${receipt.data.paid_at}</span>
      `;
      setStatus("Pago procesado.");
    } catch (error) {
      setStatus(error.message, true);
    }
  });
};

document.getElementById("btn-refresh").addEventListener("click", async () => {
  try {
    const data = await request("GET", "/payment/api/payments");
    renderList(data.data || []);
    setStatus("Pagos actualizados.");
  } catch (error) {
    setStatus(error.message, true);
  }
});

if (!token) {
  setStatus("Inicia sesion en Auth para gestionar pagos.", true);
} else {
  document.getElementById("btn-refresh").click();
  renderPanels().catch((error) => setStatus(error.message, true));
}
