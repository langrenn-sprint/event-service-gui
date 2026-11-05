// Live updates of the system page (/system), see event-service-gui#203.
//
// Polls /system/status and fills in the values the server has already
// calculated (ages, stale, warnings, health). No logic about what is OK or
// not lives here. Values are inserted with textContent, never as HTML.
(function () {
  "use strict";

  const INTERVAL_MS = 15000;
  const MAX_INTERVAL_MS = 120000;
  const FETCH_TIMEOUT_MS = 10000;

  const root = document.getElementById("system");
  if (!root || !window.fetch) {
    return;
  }
  const statusUrl = root.dataset.statusUrl;
  const initialHasStatus = root.dataset.hasStatus === "true";
  const errorLabel = document.getElementById("live-error");
  const loginLink = document.getElementById("live-login");
  const refreshButton = document.getElementById("live-refresh");

  let interval = INTERVAL_MS;
  let timer = null;
  let stopped = false;
  let inFlight = false;

  function get(obj, path) {
    return path.split(".").reduce(function (o, key) {
      return o === null || o === undefined ? undefined : o[key];
    }, obj);
  }

  function el(tag, text, className) {
    const e = document.createElement(tag);
    if (text !== undefined && text !== null) {
      e.textContent = String(text);
    }
    if (className) {
      e.className = className;
    }
    return e;
  }

  function fillFields(system) {
    root.querySelectorAll("[data-field]").forEach(function (e) {
      const value = get(system, e.dataset.field);
      const empty = e.dataset.empty || "";
      e.textContent = value === undefined || value === null || value === "" ? empty : String(value);
    });
    // data-class="path:className" toggles the class on a true value.
    root.querySelectorAll("[data-class]").forEach(function (e) {
      const parts = e.dataset.class.split(":");
      e.classList.toggle(parts[1], Boolean(get(system, parts[0])));
    });
    root.querySelectorAll("[data-show]").forEach(function (e) {
      e.hidden = !get(system, e.dataset.show);
    });
    root.querySelectorAll("[data-hide]").forEach(function (e) {
      e.hidden = Boolean(get(system, e.dataset.hide));
    });
  }

  function renderWarnings(warnings) {
    const container = document.getElementById("warnings");
    if (!container) {
      return;
    }
    const items = (warnings || []).map(function (w) {
      return el("div", w.text, "alert " + (w.level === "error" ? "alert-danger" : "alert-warning"));
    });
    if (items.length === 0) {
      items.push(el("div", "Ingen varsler.", "alert alert-success"));
    }
    container.replaceChildren.apply(container, items);
  }

  function versionCell(version) {
    const td = el("td");
    if (!version) {
      return td;
    }
    if (version.url) {
      const a = el("a");
      a.href = version.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.appendChild(el("code", version.text));
      td.appendChild(a);
    } else if (version.is_revision) {
      td.appendChild(el("code", version.text));
    } else {
      const span = el("span", version.text);
      if (version.title) {
        span.title = version.title;
      }
      td.appendChild(span);
    }
    return td;
  }

  function renderServices(services) {
    const body = document.getElementById("services-body");
    if (!body || !services) {
      return;
    }
    const rows = services.map(function (s) {
      const tr = el("tr");
      const name = el("td", s.name);
      name.title = s.image || "";
      tr.appendChild(name);
      tr.appendChild(el("td", s.state_text, s.running === false ? "danger" : ""));
      let health;
      if (s.health) {
        health = el("td", s.health.text, s.health.ok ? "" : "danger");
        health.title = s.health.detail || "";
      } else {
        health = el("td", "–");
        health.title = "Ikke sjekket (ingen HTTP-endepunkt eller ikke konfigurert)";
      }
      tr.appendChild(health);
      tr.appendChild(versionCell(s.version));
      tr.appendChild(el("td", s.image_created));
      tr.appendChild(el("td", s.started_at));
      return tr;
    });
    if (rows.length === 0) {
      const tr = el("tr");
      const td = el("td", "Ingen tjenester funnet.");
      td.colSpan = 6;
      tr.appendChild(td);
      rows.push(tr);
    }
    body.replaceChildren.apply(body, rows);
  }

  function renderDatabases(mongodb) {
    const body = document.getElementById("databases-body");
    if (!body || !mongodb) {
      return;
    }
    const rows = [];
    (mongodb.databases || []).forEach(function (db) {
      const collections = db.collections || [];
      if (collections.length === 0) {
        const tr = el("tr");
        tr.appendChild(el("td", db.name));
        tr.appendChild(el("td", db.size));
        const td = el("td", "Ingen collections");
        td.colSpan = 2;
        tr.appendChild(td);
        rows.push(tr);
        return;
      }
      collections.forEach(function (collection, i) {
        const tr = el("tr");
        tr.appendChild(el("td", i === 0 ? db.name : ""));
        tr.appendChild(el("td", i === 0 ? db.size : ""));
        tr.appendChild(el("td", collection[0]));
        tr.appendChild(el("td", collection[1]));
        rows.push(tr);
      });
    });
    body.replaceChildren.apply(body, rows);
  }

  function showError(text) {
    errorLabel.textContent = text;
    errorLabel.hidden = !text;
  }

  function render(system) {
    // The page layout differs with and without status file: reload once.
    if (Boolean(system.has_status) !== initialHasStatus) {
      window.location.reload();
      return;
    }
    fillFields(system);
    renderWarnings(system.warnings);
    renderServices(system.services);
    renderDatabases(system.mongodb);
  }

  function schedule() {
    clearTimeout(timer);
    timer = null;
    if (!stopped && document.visibilityState === "visible") {
      timer = setTimeout(poll, interval);
    }
  }

  async function poll() {
    if (stopped || inFlight) {
      return;
    }
    inFlight = true;
    refreshButton.setAttribute("aria-disabled", "true");
    refreshButton.classList.add("disabled");
    const controller = new AbortController();
    const abortTimer = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
    try {
      const resp = await fetch(statusUrl, {
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (resp.status === 401) {
        stopped = true;
        showError("Ikke innlogget som admin – oppdateringen er stoppet.");
        loginLink.hidden = false;
        return;
      }
      if (!resp.ok) {
        throw new Error("HTTP " + resp.status);
      }
      render(await resp.json());
      showError("");
      interval = INTERVAL_MS;
    } catch (e) {
      interval = Math.min(interval * 2, MAX_INTERVAL_MS);
      showError(
        "Mister kontakt med serveren – prøver igjen om " + Math.round(interval / 1000) + " s."
      );
    } finally {
      clearTimeout(abortTimer);
      inFlight = false;
      refreshButton.removeAttribute("aria-disabled");
      refreshButton.classList.remove("disabled");
      schedule();
    }
  }

  // "Oppdater nå": fetch at once and reset the backoff. After a 401 the link
  // works as a normal reload (which redirects to the login page), as it does
  // without JavaScript.
  refreshButton.addEventListener("click", function (event) {
    if (stopped) {
      return;
    }
    event.preventDefault();
    if (inFlight) {
      return;
    }
    clearTimeout(timer);
    interval = INTERVAL_MS;
    poll();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      clearTimeout(timer);
      poll();
    } else {
      clearTimeout(timer);
      timer = null;
    }
  });

  schedule();
})();
