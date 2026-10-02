"use strict";
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const state = { assets: [], offset: 0, total: 0, editId: null, deleteId: null, reports: {} };
const labels = { public: "公开", internal: "内部", confidential: "机密", passed: "通过", failed: "失败", rejected: "拒绝", duplicate: "重复" };
const scenarios = { valid_create: "正常新增", name_min: "名称最小边界", name_max: "名称最大边界", empty_name: "空名称", name_too_long: "名称超长", invalid_code: "编码格式", invalid_sensitivity: "敏感级别", duplicate_code: "编码重复" };
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const icon = (name) => `<i data-lucide="${name}"></i>`;
const icons = () => window.lucide?.createIcons();
const badge = (status) => `<span class="badge ${status}">${labels[status] || status}</span>`;
const percent = (value) => value === null ? "N/A" : `${(value * 100).toFixed(1)}%`;

function notice(message, success = false) {
  $("#notice").textContent = message;
  $("#notice").className = success ? "success" : "";
  $("#notice").hidden = false;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) {
    const error = Array.isArray(body.detail)
      ? body.detail.map((item) => `${item.loc.join(".")}: ${item.msg}`).join("; ")
      : (body.detail || `HTTP ${response.status}`);
    throw new Error(error);
  }
  return body;
}

async function busy(button, operation) {
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  try { await operation(); }
  finally { button.disabled = false; button.removeAttribute("aria-busy"); }
}

async function loadAssets() {
  const query = encodeURIComponent($("#search").value);
  const data = await api(`/api/assets?q=${query}&limit=10&offset=${state.offset}`);
  state.assets = data.items;
  state.total = data.total;
  if (!data.items.length && state.offset > 0) {
    state.offset = Math.max(0, state.offset - 10);
    return loadAssets();
  }
  $("#asset-count").textContent = `${data.total} 项资产`;
  $("#asset-empty").hidden = data.items.length > 0;
  $("#asset-rows").innerHTML = data.items.map((asset) => `<tr>
    <td class="code">${escapeHtml(asset.asset_code)}</td>
    <td>${escapeHtml(asset.name)}</td>
    <td>${escapeHtml(asset.owner)}</td>
    <td>${badge(asset.sensitivity)}</td>
    <td class="muted">${escapeHtml(new Date(asset.created_at).toLocaleString("zh-CN", { hour12: false }))}</td>
    <td><div class="row-actions"><button class="icon-button" data-edit="${asset.id}" title="编辑资产" aria-label="编辑 ${escapeHtml(asset.asset_code)}">${icon("pencil")}</button><button class="icon-button" data-delete="${asset.id}" title="删除资产" aria-label="删除 ${escapeHtml(asset.asset_code)}">${icon("trash-2")}</button></div></td>
  </tr>`).join("");
  $("#page-number").textContent = `${Math.floor(state.offset / 10) + 1} / ${Math.max(1, Math.ceil(data.total / 10))}`;
  $("#previous").disabled = state.offset === 0;
  $("#next").disabled = state.offset + 10 >= data.total;
  icons();
}

function showAsset(asset = null) {
  state.editId = asset?.id ?? null;
  $("#asset-form").reset();
  $("#asset-error").hidden = true;
  $("#dialog-title").textContent = asset ? "编辑资产" : "新增资产";
  if (asset) {
    for (const field of ["asset_code", "name", "owner", "sensitivity"]) {
      $("#asset-form").elements.namedItem(field).value = asset[field];
    }
  }
  $("#asset-dialog").showModal();
}

$("#add-asset").addEventListener("click", () => showAsset());
$("#asset-rows").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit]");
  const remove = event.target.closest("[data-delete]");
  if (edit) showAsset(state.assets.find((asset) => asset.id === Number(edit.dataset.edit)));
  if (remove) {
    const asset = state.assets.find((asset) => asset.id === Number(remove.dataset.delete));
    state.deleteId = asset.id;
    $("#delete-label").textContent = `${asset.asset_code} · ${asset.name}`;
    $("#delete-dialog").showModal();
  }
});
$("#asset-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await busy($("#save-asset"), async () => {
    try {
      const payload = Object.fromEntries(new FormData(event.target));
      const path = state.editId === null ? "/api/assets" : `/api/assets/${state.editId}`;
      await api(path, { method: state.editId === null ? "POST" : "PUT", body: JSON.stringify(payload) });
      $("#asset-dialog").close();
      notice("资产已保存", true);
      await loadAssets();
    } catch (error) {
      $("#asset-error").textContent = error.message;
      $("#asset-error").hidden = false;
    }
  });
});
$("#confirm-delete").addEventListener("click", async () => {
  await busy($("#confirm-delete"), async () => {
    try {
      await api(`/api/assets/${state.deleteId}`, { method: "DELETE" });
      $("#delete-dialog").close();
      notice("资产已删除", true);
      await loadAssets();
    } catch (error) { notice(error.message); }
  });
});
$$("[data-close]").forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.close}`).close()));
$("#search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  state.offset = 0;
  loadAssets().catch((error) => notice(error.message));
});
$("#refresh").addEventListener("click", () => loadAssets().catch((error) => notice(error.message)));
for (const [id, delta] of [["previous", -10], ["next", 10]]) {
  $(`#${id}`).addEventListener("click", () => {
    state.offset += delta;
    loadAssets().catch((error) => notice(error.message));
  });
}

function selectTab(button) {
  $$("[data-view]").forEach((tab) => {
    const selected = tab === button;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    $(`#${tab.dataset.view}`).hidden = !selected;
  });
  $("#notice").hidden = true;
}
$$("[data-view]").forEach((button) => {
  button.addEventListener("click", () => selectTab(button));
  button.addEventListener("keydown", (event) => {
    const tabs = $$("[data-view]");
    let index = tabs.indexOf(button);
    if (event.key === "ArrowRight") index = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") index = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") index = 0;
    else if (event.key === "End") index = tabs.length - 1;
    else return;
    event.preventDefault();
    selectTab(tabs[index]);
    tabs[index].focus();
  });
});

function clearReport(kind) {
  state.reports[kind] = null;
  $(`#${kind}-report`).hidden = true;
  $(`[data-download="${kind}"]`).disabled = true;
}
for (const kind of ["quality", "cases"]) {
  $(`#${kind}-input`).addEventListener("input", () => clearReport(kind));
}
async function loadExample(kind) {
  const data = await api(`/api/examples/${kind}`);
  $(`#${kind}-input`).value = JSON.stringify(data, null, 2);
  $(`#${kind}-error`).hidden = true;
  clearReport(kind);
}
$$("[data-example]").forEach((button) => button.addEventListener("click", () =>
  busy(button, () => loadExample(button.dataset.example)).catch((error) => notice(error.message))));

function metrics(target, entries) {
  $(target).innerHTML = entries.map(([label, value]) =>
    `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`
  ).join("");
}
function renderQuality(report) {
  metrics("#quality-metrics", [["记录数", report.total], ["合格记录", report.valid], ["问题记录", report.invalid], ["记录合格率", percent(report.valid_rate)]]);
  $("#quality-results").innerHTML = report.rows.map((row) =>
    `<tr><td class="code">#${row.row}</td><td>${badge(row.valid ? "passed" : "failed")}</td><td>${row.issues.map((issue) => `${escapeHtml(issue.field)}: ${escapeHtml(issue.message)}`).join("<br>") || "—"}</td></tr>`
  ).join("");
}
function renderCases(report) {
  metrics("#cases-metrics", [["提交 / 执行", `${report.total} / ${report.executed}`], ["格式合格率", percent(report.schema_valid_rate)], ["断言通过率", percent(report.assertion_pass_rate)], ["场景覆盖率", percent(report.scenario_coverage)]]);
  $("#coverage-count").textContent = `${report.covered_scenarios.length} / ${report.scenario_total}`;
  $("#coverage-grid").innerHTML = Object.entries(scenarios).map(([key, label]) => {
    const covered = report.covered_scenarios.includes(key);
    return `<div class="coverage ${covered ? "covered" : ""}">${icon(covered ? "circle-check" : "circle-minus")}<span>${label}</span></div>`;
  }).join("");
  $("#cases-results").innerHTML = report.results.map((result) => {
    const status = result.actual_status === undefined ? "—" : `${result.expected_status} / ${result.actual_status}`;
    const issues = (result.issues || []).map((issue) => `${escapeHtml(issue.field)}: ${escapeHtml(issue.message)}`).join("<br>");
    const mismatch = result.scenario_matches === false ? `<span class="badge rejected">场景标签不匹配</span>` : "";
    const details = result.actual ? `<details><summary>响应与字段断言</summary><pre>${escapeHtml(JSON.stringify({ field_matches: result.field_matches, response: result.actual }, null, 2))}</pre></details>` : "";
    return `<tr><td>${escapeHtml(result.name)}</td><td>${badge(result.status)}</td><td class="code">${status}</td><td>${issues}${mismatch}${details}</td></tr>`;
  }).join("");
  icons();
}
for (const kind of ["quality", "cases"]) {
  $(`#run-${kind}`).addEventListener("click", () => busy($(`#run-${kind}`), async () => {
    clearReport(kind);
    $(`#${kind}-error`).hidden = true;
    const input = $(`#${kind}-input`);
    input.readOnly = true;
    try {
      const parsed = JSON.parse(input.value);
      if (!Array.isArray(parsed)) throw new Error("请输入 JSON 数组");
      const payload = kind === "quality" ? { records: parsed } : { cases: parsed };
      const report = await api(kind === "quality" ? "/api/quality/check" : "/api/cases/evaluate", { method: "POST", body: JSON.stringify(payload) });
      state.reports[kind] = report;
      if (kind === "quality") renderQuality(report); else renderCases(report);
      $(`#${kind}-report`).hidden = false;
      $(`[data-download="${kind}"]`).disabled = false;
    } catch (error) {
      $(`#${kind}-error`).textContent = error.message;
      $(`#${kind}-error`).hidden = false;
    } finally { input.readOnly = false; }
  }));
}
$$("[data-download]").forEach((button) => button.addEventListener("click", () => {
  const kind = button.dataset.download;
  const report = state.reports[kind];
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${kind}-report.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}));

icons();
api("/health").then(() => { $("#health").textContent = "服务在线"; $("#health").classList.add("online"); }).catch(() => { $("#health").textContent = "服务离线"; });
loadAssets().catch((error) => notice(error.message));
Promise.all([loadExample("quality"), loadExample("cases")]).catch((error) => notice(error.message));
