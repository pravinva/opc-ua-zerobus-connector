/* global React, ReactDOM */

function useInterval(callback, delayMs) {
  const savedRef = React.useRef(callback);
  React.useEffect(() => {
    savedRef.current = callback;
  }, [callback]);

  React.useEffect(() => {
    if (delayMs == null) return;
    const id = setInterval(() => savedRef.current(), delayMs);
    return () => clearInterval(id);
  }, [delayMs]);
}

async function apiGet(path) {
  const r = await fetch(path, { headers: { Accept: "application/json" } });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}

async function apiPost(path, payload) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}

async function apiPatch(path, payload) {
  // server implements patch as POST for simplicity
  return await apiPost(path, payload);
}

async function apiDelete(path) {
  const r = await fetch(path, { method: "DELETE", headers: { Accept: "application/json" } });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}

function Card(props) {
  return React.createElement("div", { className: `card ${props.className || ""}`.trim() }, props.children);
}

function Row(props) {
  return React.createElement("div", { className: "row" }, props.children);
}

function Stack(props) {
  return React.createElement("div", { className: "stack" }, props.children);
}

function Field(props) {
  const help = props.help ? String(props.help) : "";
  return React.createElement(
    "div",
    { className: "field" },
    React.createElement(
      "div",
      { className: "fieldLabel", title: help },
      props.label,
      help ? React.createElement("span", { className: "fieldInfo", title: help }, "i") : null
    ),
    props.children
  );
}

function App() {
  const [status, setStatus] = React.useState(null);
  const [sources, setSources] = React.useState([]);
  const [runningSources, setRunningSources] = React.useState([]);
  const [sourceErrors, setSourceErrors] = React.useState({});
  const [showStatusRaw, setShowStatusRaw] = React.useState(false);

  const [cfg, setCfg] = React.useState(null);
  const [cfgText, setCfgText] = React.useState("");

  const [newSourceName, setNewSourceName] = React.useState("");
  const [newSourceEndpoint, setNewSourceEndpoint] = React.useState("");
  const [testingName, setTestingName] = React.useState(null);

  const [error, setError] = React.useState(null);
  const [saving, setSaving] = React.useState(false);

  // Databricks/Zerobus settings
  const [dbxHost, setDbxHost] = React.useState("");
  const [zerobusEndpoint, setZerobusEndpoint] = React.useState("");
  const [targetCatalog, setTargetCatalog] = React.useState("");
  const [targetSchema, setTargetSchema] = React.useState("");
  const [targetTable, setTargetTable] = React.useState("");
  const [clientIdEnv, setClientIdEnv] = React.useState("DBX_CLIENT_ID");
  const [clientSecretEnv, setClientSecretEnv] = React.useState("DBX_CLIENT_SECRET");
  const [maxInflight, setMaxInflight] = React.useState("1000");
  const [flushTimeoutMs, setFlushTimeoutMs] = React.useState("60000");
  const [ackTimeoutMs, setAckTimeoutMs] = React.useState("60000");
  const [recovery, setRecovery] = React.useState(true);
  const [envStatus, setEnvStatus] = React.useState(null);

  const hasError = Boolean(status && status.last_error);
  const isStreaming = Array.isArray(runningSources) && runningSources.length > 0;
  const credsLoaded = Boolean(envStatus && envStatus.client_id_set && envStatus.client_secret_set);

  const refresh = React.useCallback(async () => {
    try {
      setError(null);
      const [s, c, src, env] = await Promise.all([
        apiGet("/api/status"),
        apiGet("/api/config"),
        apiGet("/api/sources"),
        apiGet("/api/databricks/env_status").catch(() => null),
      ]);

      setStatus(s);
      setRunningSources(Array.isArray(s.running_sources) ? s.running_sources : []);
      setSourceErrors(s.source_last_error && typeof s.source_last_error === "object" ? s.source_last_error : {});

      setCfg(c);
      setCfgText(JSON.stringify(c, null, 2));

      setSources(Array.isArray(src) ? src : []);
      setEnvStatus(env);

      const dbx = (c && c.databricks) || {};
      setDbxHost(dbx.workspace_host || "");
      setZerobusEndpoint(dbx.zerobus_endpoint || "");
      const tgt = dbx.target || {};
      setTargetCatalog(tgt.catalog || "");
      setTargetSchema(tgt.schema || "");
      setTargetTable(tgt.table || "");
      const a = dbx.auth || {};
      setClientIdEnv(a.client_id_env || "DBX_CLIENT_ID");
      setClientSecretEnv(a.client_secret_env || "DBX_CLIENT_SECRET");
      const st = dbx.stream || {};
      setMaxInflight(String(st.max_inflight_records ?? 1000));
      setFlushTimeoutMs(String(st.flush_timeout_ms ?? 60000));
      setAckTimeoutMs(String(st.server_lack_of_ack_timeout_ms ?? 60000));
      setRecovery(Boolean(st.recovery ?? true));

    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  useInterval(() => {
    apiGet("/api/status")
      .then((s) => {
        setStatus(s);
        setRunningSources(Array.isArray(s.running_sources) ? s.running_sources : []);
        setSourceErrors(s.source_last_error && typeof s.source_last_error === "object" ? s.source_last_error : {});
      })
      .catch((e) => setError(String(e && e.message ? e.message : e)));
  }, 2000);

  async function onAddSource() {
    try {
      setError(null);
      await apiPost("/api/sources", {
        name: newSourceName.trim(),
        endpoint: newSourceEndpoint.trim(),
      });
      setNewSourceName("");
      setNewSourceEndpoint("");
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onDeleteSource(name) {
    try {
      setError(null);
      await apiDelete(`/api/sources/${encodeURIComponent(name)}`);
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onTestSource(name) {
    try {
      setTestingName(name);
      setError(null);
      const res = await apiPost(`/api/sources/${encodeURIComponent(name)}/test`, {});
      if (res.ok) {
        let info = `✓ ${(res.protocol_type || "").toUpperCase()} Connection OK`;
        if (res.server_info) {
          const serverInfo = Object.entries(res.server_info)
            .map(([k, v]) => `${k}: ${v}`)
            .join("\n");
          if (serverInfo) info += `\n\n${serverInfo}`;
        }
        alert(info);
      } else {
        alert(`✗ ${(res.protocol_type || "Connection").toUpperCase()} Failed\n${res.error || ""}`);
      }
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    } finally {
      setTestingName(null);
    }
  }

  async function onStartSource(name) {
    try {
      setError(null);
      await apiPost(`/api/sources/${encodeURIComponent(name)}/start`, {});
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onStopSource(name) {
    try {
      setError(null);
      await apiPost(`/api/sources/${encodeURIComponent(name)}/stop`, {});
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onStartAll() {
    try {
      setError(null);
      const names = (sources || []).map((s) => s.name).filter(Boolean);
      await Promise.allSettled(names.map((n) => apiPost(`/api/sources/${encodeURIComponent(n)}/start`, {})));
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onStopAll() {
    try {
      setError(null);
      const names = (sources || []).map((s) => s.name).filter(Boolean);
      await Promise.allSettled(names.map((n) => apiPost(`/api/sources/${encodeURIComponent(n)}/stop`, {})));
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onSaveDbx() {
    try {
      setSaving(true);
      setError(null);
      await apiPatch("/api/config/patch", {
        databricks: {
          workspace_host: dbxHost.trim(),
          zerobus_endpoint: zerobusEndpoint.trim(),
          auth: {
            client_id_env: clientIdEnv.trim() || "DBX_CLIENT_ID",
            client_secret_env: clientSecretEnv.trim() || "DBX_CLIENT_SECRET",
            scope: "all-apis",
          },
          target: {
            catalog: targetCatalog.trim(),
            schema: targetSchema.trim(),
            table: targetTable.trim(),
          },
          stream: {
            record_type: "JSON",
            max_inflight_records: parseInt(maxInflight || "1000", 10),
            recovery: Boolean(recovery),
            flush_timeout_ms: parseInt(flushTimeoutMs || "60000", 10),
            server_lack_of_ack_timeout_ms: parseInt(ackTimeoutMs || "60000", 10),
          },
        },
      });
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    } finally {
      setSaving(false);
    }
  }

  async function onSaveAdvanced() {
    try {
      setSaving(true);
      setError(null);
      const next = JSON.parse(cfgText);
      await apiPost("/api/config", next);
      await refresh();
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    } finally {
      setSaving(false);
    }
  }

  async function onTestDbxAuth() {
    try {
      setError(null);
      const res = await apiPost("/api/databricks/test_auth", {});
      alert(res.ok ? `Databricks auth OK\n${res.token_endpoint_used}` : `Databricks auth failed\n${res.error}`);
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  async function onTestZerobusWrite() {
    try {
      setError(null);
      const res = await apiPost("/api/zerobus/test_ingest", {});
      alert(res.ok ? `Zerobus ingest OK\nstream_id=${res.stream_id}` : `Zerobus ingest failed\n${res.error}`);
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
    }
  }

  return React.createElement(
    "div",
    { className: "container" },
    React.createElement(
      "div",
      { className: "topbar" },
      React.createElement(
        "div",
        { className: "brand" },
        React.createElement("div", { className: "dbxMark" }),
        React.createElement(
          "div",
          null,
          React.createElement("div", { className: "title" }, "Databricks IoT Connector"),
          React.createElement("div", { className: "subtitle" }, "OPC-UA · MQTT · Modbus → Zerobus")
        )
      ),
      React.createElement(
        "div",
        { className: "topbarRight" },
        React.createElement("div", {
          className: hasError ? "statusDot statusDot--error" : (isStreaming ? "statusDot statusDot--ok" : "statusDot statusDot--idle")
        }),
        React.createElement("div", { className: "statusText" },
          hasError ? "Error" : (isStreaming ? "Streaming" : "Stopped")
        )
      )
    ),
    error ? React.createElement("div", { className: "error" }, error) : null,

    React.createElement(
      "div",
      { className: "grid" },

      React.createElement(
        Card,
        { className: "span2" },
        React.createElement("div", { className: "cardTitle" }, "Databricks / Zerobus"),
        React.createElement(
          Stack,
          null,
          React.createElement(
            "div",
            { className: "pill" },
            React.createElement("div", {
              className: envStatus ? (credsLoaded ? "statusDot statusDot--ok" : "statusDot statusDot--error") : "statusDot statusDot--idle",
            }),
            React.createElement(
              "div",
              null,
              React.createElement(
                "div",
                { className: "pillTitle" },
                "Credentials: ",
                envStatus ? (credsLoaded ? "loaded" : "missing") : "unknown"
              ),
              React.createElement(
                "div",
                { className: "pillHelp" },
                envStatus
                  ? `${envStatus.client_id_env} (${envStatus.client_id_len}) · ${envStatus.client_secret_env} (${envStatus.client_secret_len})`
                  : "Restart the connector after setting env vars."
              )
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              Field,
              {
                label: "Workspace",
                help: "Databricks workspace host (OAuth): https://<workspace>.cloud.databricks.com",
              },
              React.createElement("input", {
                className: "input",
                value: dbxHost,
                placeholder: "https://e2-demo-field-eng.cloud.databricks.com",
                onChange: (e) => setDbxHost(e.target.value),
              })
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              Field,
              {
                label: "Zerobus endpoint",
                help: "<wsid>.zerobus.<region>.cloud.databricks.com",
              },
              React.createElement("input", {
                className: "input",
                value: zerobusEndpoint,
                placeholder: "1444828305810485.zerobus.us-west-2.cloud.databricks.com",
                onChange: (e) => setZerobusEndpoint(e.target.value),
              })
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              Field,
              { label: "Catalog", help: "Unity Catalog catalog (example: opcua)" },
              React.createElement("input", { className: "input", value: targetCatalog, placeholder: "opcua", onChange: (e) => setTargetCatalog(e.target.value) })
            ),
            React.createElement(
              Field,
              { label: "Schema", help: "Unity Catalog schema (example: scada_data)" },
              React.createElement("input", { className: "input", value: targetSchema, placeholder: "scada_data", onChange: (e) => setTargetSchema(e.target.value) })
            ),
            React.createElement(
              Field,
              { label: "Table", help: "Destination table (example: opcua_events_bronze)" },
              React.createElement("input", { className: "input", value: targetTable, placeholder: "opcua_events_bronze", onChange: (e) => setTargetTable(e.target.value) })
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              Field,
              { label: "Client ID env", help: "Env var name (example: DBX_CLIENT_ID)" },
              React.createElement("input", { className: "input", value: clientIdEnv, placeholder: "DBX_CLIENT_ID", onChange: (e) => setClientIdEnv(e.target.value) })
            ),
            React.createElement(
              Field,
              { label: "Client Secret env", help: "Env var name (example: DBX_CLIENT_SECRET)" },
              React.createElement("input", { className: "input", value: clientSecretEnv, placeholder: "DBX_CLIENT_SECRET", onChange: (e) => setClientSecretEnv(e.target.value) })
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              Field,
              { label: "Max inflight", help: "Max unacknowledged records (example: 1000)" },
              React.createElement("input", { className: "input", value: maxInflight, placeholder: "1000", onChange: (e) => setMaxInflight(e.target.value) })
            ),
            React.createElement(
              Field,
              { label: "Flush timeout", help: "ms (example: 60000)" },
              React.createElement("input", { className: "input", value: flushTimeoutMs, placeholder: "60000", onChange: (e) => setFlushTimeoutMs(e.target.value) })
            ),
            React.createElement(
              Field,
              { label: "Ack timeout", help: "ms (example: 60000)" },
              React.createElement("input", { className: "input", value: ackTimeoutMs, placeholder: "60000", onChange: (e) => setAckTimeoutMs(e.target.value) })
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement(
              "label",
              { className: "fieldCheckbox" },
              React.createElement("input", { type: "checkbox", checked: recovery, onChange: (e) => setRecovery(e.target.checked) }),
              "  Recovery"
            ),
            React.createElement(
              "button",
              { className: "button buttonSmall buttonSecondary", onClick: onTestDbxAuth },
              "Test DBX Auth"
            ),
            React.createElement(
              "button",
              { className: "button buttonSmall buttonSecondary", onClick: onTestZerobusWrite },
              "Test Zerobus Write"
            ),
            React.createElement(
              "button",
              { className: "button", onClick: onSaveDbx, disabled: saving },
              saving ? "Saving…" : "Save"
            )
          )
        )
      ),

      React.createElement(
        Card,
        { className: "span2" },
        React.createElement("div", { className: "cardTitle" }, "OPC UA Sources"),
        React.createElement("div", { className: "muted" }, "Start streaming sends OPC UA updates to the configured Unity Catalog table via Zerobus."),
        React.createElement(
          Stack,
          null,
          React.createElement(
            Row,
            null,
            React.createElement(
              "button",
              { className: "button buttonSmall buttonSecondary", onClick: refresh },
              "Refresh"
            ),
            React.createElement(
              "button",
              { className: "button buttonSmall buttonSecondary", onClick: onStartAll, disabled: !sources || !sources.length },
              "Start all"
            ),
            React.createElement(
              "button",
              { className: "button buttonSmall buttonDanger", onClick: onStopAll, disabled: !sources || !sources.length },
              "Stop all"
            )
          ),
          React.createElement(
            Row,
            null,
            React.createElement("input", {
              className: "input",
              placeholder: "name (e.g. prosys-sim)",
              value: newSourceName,
              onChange: (e) => setNewSourceName(e.target.value),
            }),
            React.createElement("input", {
              className: "input",
              placeholder: "endpoint (opc.tcp://, mqtt://, modbus://...)",
              value: newSourceEndpoint,
              onChange: (e) => setNewSourceEndpoint(e.target.value),
            }),
            React.createElement(
              "button",
              {
                className: "button",
                onClick: onAddSource,
                disabled: !newSourceName.trim() || !newSourceEndpoint.trim(),
              },
              "Add"
            )
          ),

          sources && sources.length
            ? React.createElement(
                "div",
                { className: "list" },
                sources.map((s) => {
                  const name = s.name || "";
                  const running = runningSources.includes(name);
                  return React.createElement(
                    "div",
                    { key: name || s.endpoint, className: "listRow" },
                    React.createElement(
                      "div",
                      { className: "listMain" },
                      React.createElement(
                        "div",
                        { style: { display: "flex", alignItems: "center", gap: "8px" } },
                        React.createElement("div", { className: "listName" }, name || "(no name)"),
                        s.protocol_type
                          ? React.createElement(
                              "span",
                              {
                                style: {
                                  fontSize: "10px",
                                  fontWeight: "800",
                                  padding: "2px 6px",
                                  borderRadius: "6px",
                                  background: s.protocol_type === "opcua" ? "rgba(31,111,235,0.12)" : (s.protocol_type === "mqtt" ? "rgba(16,185,129,0.12)" : "rgba(245,158,11,0.12)"),
                                  color: s.protocol_type === "opcua" ? "#1f6feb" : (s.protocol_type === "mqtt" ? "#10b981" : "#f59e0b"),
                                  textTransform: "uppercase",
                                  letterSpacing: "0.05em",
                                },
                              },
                              s.protocol_type
                            )
                          : null
                      ),
                      React.createElement("div", { className: "listMeta", title: s.endpoint || "" }, s.endpoint || ""),
                      sourceErrors && sourceErrors[name]
                        ? React.createElement("div", { className: "listError" }, sourceErrors[name])
                        : null
                    ),
                    React.createElement(
                      "div",
                      { className: "listActions" },
                      React.createElement(
                        "button",
                        {
                          className: "button buttonSmall buttonSecondary",
                          onClick: () => onTestSource(name),
                          disabled: !name || testingName === name,
                        },
                        testingName === name ? "Testing…" : "Test Connection"
                      ),
                      React.createElement(
                        "button",
                        {
                          className: "button buttonSmall buttonSecondary",
                          onClick: () => onStartSource(name),
                          disabled: !name || running,
                        },
                        running ? "Streaming" : "Start streaming"
                      ),
                      React.createElement(
                        "button",
                        {
                          className: "button buttonSmall buttonDanger",
                          onClick: () => onStopSource(name),
                          disabled: !name || !running,
                        },
                        "Stop streaming"
                      ),
                      React.createElement(
                        "button",
                        {
                          className: "button buttonSmall buttonDanger",
                          onClick: () => onDeleteSource(name),
                          disabled: !name,
                        },
                        "Remove"
                      )
                    )
                  );
                })
              )
            : React.createElement("div", { className: "muted" }, "No sources configured yet.")
        )
      ),

      React.createElement(
        Card,
        null,
        React.createElement("div", { className: "cardTitle" }, "Config (advanced)"),
        cfg
          ? React.createElement(
              React.Fragment,
              null,
              React.createElement("textarea", {
                className: "textarea",
                value: cfgText,
                onChange: (e) => setCfgText(e.target.value),
                spellCheck: false,
              }),
              React.createElement(
                Row,
                null,
                React.createElement(
                  "button",
                  { className: "button", onClick: onSaveAdvanced, disabled: saving },
                  saving ? "Saving…" : "Save"
                ),
                React.createElement(
                  "a",
                  {
                    className: "link",
                    href: `http://${location.hostname}:9090/metrics`,
                    target: "_blank",
                    rel: "noreferrer",
                  },
                  "Metrics"
                )
              )
            )
          : React.createElement("div", { className: "muted" }, "Loading…")
      ),

      React.createElement(
        Card,
        null,
        React.createElement("div", { className: "cardTitle" }, "Status"),
        status
          ? React.createElement(
              React.Fragment,
              null,
              React.createElement(
                "div",
                { className: "statusSummary" },
                React.createElement("div", { className: "statusItem" }, React.createElement("div", { className: "statusKey" }, "Connected sources"), React.createElement("div", { className: "statusVal" }, String(status.connected_sources ?? 0))),
                React.createElement("div", { className: "statusItem" }, React.createElement("div", { className: "statusKey" }, "Events ingested"), React.createElement("div", { className: "statusVal" }, String(status.events_ingested ?? 0))),
                React.createElement("div", { className: "statusItem" }, React.createElement("div", { className: "statusKey" }, "Events sent"), React.createElement("div", { className: "statusVal" }, String(status.events_sent ?? 0))),
                React.createElement("div", { className: "statusItem" }, React.createElement("div", { className: "statusKey" }, "Streaming"), React.createElement("div", { className: "statusVal" }, String((status.running_sources || []).length)))
              ),
              status.last_error ? React.createElement("div", { className: "listError" }, String(status.last_error)) : null,
              React.createElement(
                Row,
                null,
                React.createElement(
                  "button",
                  { className: "button buttonSmall buttonSecondary", onClick: () => setShowStatusRaw(!showStatusRaw) },
                  showStatusRaw ? "Hide raw JSON" : "Show raw JSON"
                )
              ),
              showStatusRaw ? React.createElement("pre", { className: "pre" }, JSON.stringify(status, null, 2)) : null
            )
          : React.createElement("div", { className: "muted" }, "Loading…")
      )
    )
  );
}

ReactDOM.render(React.createElement(App), document.getElementById("root"));
