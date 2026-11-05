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
  // Keep the refresh icon spinning a little, so a fast fetch is still seen.
  const MIN_BUSY_MS = 600;

  const root = document.getElementById("system");
  if (!root) {
    return;
  }

  // Explanations (i): some mobile browsers do not focus a tapped button, so
  // toggle them on click too. Tapping elsewhere closes them.
  document.addEventListener("click", function (event) {
    const tip = event.target.closest(".info-tip");
    root.querySelectorAll(".info-tip.open").forEach(function (e) {
      if (e !== tip) {
        e.classList.remove("open");
      }
    });
    if (tip) {
      tip.classList.toggle("open");
    }
  });

  // Open the explanation to the right if it fits, otherwise to the left.
  // The best side depends on the layout (e.g. one or two columns), so it is
  // chosen when the explanation is about to be shown. Without JavaScript the
  // info-tip-left class from the template is used as is.
  const TIP_WIDTH = 330; // max-width in system.html plus margin
  function placeTip(event) {
    const tip = event.target.closest && event.target.closest(".info-tip");
    if (!tip) {
      return;
    }
    const rect = tip.getBoundingClientRect();
    const viewport = document.documentElement.clientWidth;
    const fitsRight = rect.left + Math.min(TIP_WIDTH, viewport * 0.8) <= viewport;
    const fitsLeft = rect.right - Math.min(TIP_WIDTH, viewport * 0.8) >= 0;
    tip.classList.toggle("info-tip-left", !fitsRight && fitsLeft);
  }
  ["mouseover", "focusin", "pointerdown"].forEach(function (type) {
    document.addEventListener(type, placeTip);
  });

  if (!window.fetch) {
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
  let busySince = 0;

  function setBusy(busy) {
    if (busy) {
      busySince = Date.now();
      refreshButton.classList.add("busy", "disabled");
      refreshButton.setAttribute("aria-disabled", "true");
      return;
    }
    setTimeout(function () {
      if (!inFlight) {
        refreshButton.classList.remove("busy", "disabled");
        refreshButton.removeAttribute("aria-disabled");
      }
    }, Math.max(0, MIN_BUSY_MS - (Date.now() - busySince)));
  }

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
    // data-class="path:className [path:className ...]" toggles each class
    // on a true value.
    root.querySelectorAll("[data-class]").forEach(function (e) {
      e.dataset.class.trim().split(/\s+/).forEach(function (pair) {
        const parts = pair.split(":");
        e.classList.toggle(parts[1], Boolean(get(system, parts[0])));
      });
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

  // Memory of a service: amount, share of the machine's memory and, if the
  // container has its own limit, the share of that limit on a second line.
  function memoryCell(s) {
    const td = el("td", s.memory_text);
    if (s.memory_share) {
      td.appendChild(document.createTextNode(" "));
      td.appendChild(el("span", "(" + s.memory_share + ")", "text-muted"));
    }
    if (s.memory_limit_text) {
      td.appendChild(el("br"));
      td.appendChild(el("small", s.memory_limit_text, "text-muted"));
    }
    return td;
  }

  // Sorting of the services table. The server sends sort keys per service
  // (service.sort), where ascending order puts the most interesting first.
  // A click sorts by a column, the next click reverses it. No value (null)
  // is always last. The choice is kept in localStorage.
  const SORT_STORAGE = "system.servicesSort";
  let sortState = { key: null, reversed: false };
  let lastServices = null;
  try {
    sortState = JSON.parse(localStorage.getItem(SORT_STORAGE)) || sortState;
  } catch (e) {
    // ignore: no storage or invalid value
  }

  function compareKeys(a, b) {
    if (Array.isArray(a) && Array.isArray(b)) {
      for (let i = 0; i < Math.min(a.length, b.length); i++) {
        const c = compareKeys(a[i], b[i]);
        if (c !== 0) {
          return c;
        }
      }
      return a.length - b.length;
    }
    if (typeof a === "string" && typeof b === "string") {
      return a.localeCompare(b, "nb");
    }
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function sortServices(services) {
    const key = sortState.key;
    if (!key) {
      return services;
    }
    return services.slice().sort(function (x, y) {
      const a = x.sort ? x.sort[key] : null;
      const b = y.sort ? y.sort[key] : null;
      const aMissing = a === null || a === undefined;
      const bMissing = b === null || b === undefined;
      let c = 0;
      if (aMissing !== bMissing) {
        return aMissing ? 1 : -1; // no value last, in both directions
      }
      if (!aMissing) {
        c = compareKeys(a, b);
        if (sortState.reversed) {
          c = -c;
        }
      }
      return c !== 0 ? c : compareKeys(x.name || "", y.name || "");
    });
  }

  function updateSortHeaders() {
    document.querySelectorAll("#services th[data-sort]").forEach(function (th) {
      const icon = th.querySelector(".sort-icon");
      if (!icon) {
        return;
      }
      if (th.dataset.sort !== sortState.key) {
        th.removeAttribute("aria-sort");
        icon.className = "glyphicon glyphicon-sort sort-icon";
        return;
      }
      const flip = { ascending: "descending", descending: "ascending", other: "other" };
      const first = th.dataset.first || "ascending";
      th.setAttribute("aria-sort", sortState.reversed ? flip[first] : first);
      icon.className = "glyphicon sort-icon " +
        (sortState.reversed ? "glyphicon-triangle-top" : "glyphicon-triangle-bottom");
    });
  }

  function setUpSortHeaders() {
    document.querySelectorAll("#services th[data-sort]").forEach(function (th) {
      const label = th.querySelector(".sort-label");
      if (!label) {
        return;
      }
      const button = el("button", null, "sort-btn");
      button.type = "button";
      button.title = "Sorter etter " + label.textContent.toLowerCase();
      button.appendChild(el("span", label.textContent));
      const icon = el("span", null, "glyphicon glyphicon-sort sort-icon");
      icon.setAttribute("aria-hidden", "true");
      button.appendChild(icon);
      label.replaceWith(button);
      button.addEventListener("click", function () {
        const key = th.dataset.sort;
        sortState = sortState.key === key
          ? { key: key, reversed: !sortState.reversed }
          : { key: key, reversed: false };
        try {
          localStorage.setItem(SORT_STORAGE, JSON.stringify(sortState));
        } catch (e) {
          // ignore: no storage
        }
        updateSortHeaders();
        if (lastServices) {
          renderServices(lastServices);
        } else {
          poll(); // the page was rendered by the server: get the sort keys
        }
      });
    });
    updateSortHeaders();
  }

  function renderServices(services) {
    const body = document.getElementById("services-body");
    if (!body || !services) {
      return;
    }
    lastServices = services;
    const rows = sortServices(services).map(function (s) {
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
      tr.appendChild(memoryCell(s));
      tr.appendChild(el("td", s.cpu_text));
      tr.appendChild(versionCell(s.version));
      tr.appendChild(el("td", s.image_created));
      tr.appendChild(el("td", s.started_at));
      return tr;
    });
    if (rows.length === 0) {
      const tr = el("tr");
      const td = el("td", "Ingen tjenester funnet.");
      td.colSpan = 8;
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
    setBusy(true);
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
      setBusy(false);
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

  setUpSortHeaders();
  if (sortState.key) {
    poll(); // sort the server-rendered table as chosen last time
  } else {
    schedule();
  }
})();
