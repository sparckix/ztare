import React from "react";
import {
  Accordion,
  Alert,
  Anchor,
  Badge,
  Box,
  Button,
  Card,
  Code,
  Divider,
  Group,
  NativeSelect,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title
} from "./leanmill-ui.jsx";
import { displayMessage, displayText, isPreviewableRepoPath } from "../design-system.js";

export function emptyLeanMillBlueprintDraft() {
  return {
    project: "",
    slug: "",
    title: "",
    target_statement: "",
    notes: "",
    non_claims_text: "This isn't a verified result until Lean checks the proof and the work is saved."
  };
}

export function emptyLeanMillActionDraft() {
  return {
    notes_path: "",
    target_name: "",
    source_file: "",
    goal: "",
    provider: "",
    mode: "dag_search",
    timeout_s: "500",
    project: "",
    substrate: ""
  };
}

function normalizeLeanMillView(view) {
  const requested = String(view || "Start").trim();
  return ["Start", "Draft target", "Run a proof", "Proof files", "Proof status"].includes(requested) ? requested : "Start";
}


// Translate the kernel's proof vocabulary into what a human needs to know. A clean Lean compile is a
// *candidate* — trusted only once it's reviewed and approved (credit_ready).
function leanProofVerdict(row = {}) {
  const credit = String(row.credit_status || "").toLowerCase();
  const exit = String(row.typed_exit_kind || "").toLowerCase();
  const lever = String(row.next_lever || "").toLowerCase();
  const residual = String(row.residual_class || "").toLowerCase();
  let label = "In progress", tone = "gray";
  if (credit === "credit_ready") { label = "Verified"; tone = "green"; }
  else if (/closure/.test(exit) || row.compile_ok === true) { label = "Awaiting approval"; tone = "blue"; }
  else if (row.compile_ok === false || /fail/.test(exit)) { label = "Did not compile"; tone = "red"; }
  const nextMap = { ratify_closure: "send it for approval", route_to_governance: "send it for review" };
  const next = nextMap[lever] || (lever ? lever.replace(/_/g, " ") : "");
  const gap = residual && residual !== "none_closed" ? `Open gap: ${residual.replace(/_/g, " ")}.` : "";
  return { label, tone, next, gap };
}

// Make a raw proof identifier human: "adhoc::cost_eq_statePriceWeighted_payoff" → kind "ad hoc" + the
// Lean declaration name (kept in code font — snake_case IS the theorem id, not prose to reword).
function humanizeTarget(raw) {
  const s = String(raw || "").trim();
  if (!s) return { kind: "", name: "target" };
  const i = s.indexOf("::");
  if (i === -1) return { kind: "", name: s };
  return { kind: s.slice(0, i).replace(/_/g, " "), name: s.slice(i + 2) || s };
}

// De-boxed to the workbench design language: an eyebrow + title + content, separated by a hairline —
// not a shadowed card. Matches the rest of the workbench (typography + hairlines, no card-soup).
function SectionCard({ eyebrow, title, description, children, ...rest }) {
  return (
    <Box className="leanmill-section" {...rest}>
      {eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}
      {title ? <h3 className="leanmill-section-title">{title}</h3> : null}
      {description ? <p className="leanmill-section-desc">{displayText(description)}</p> : null}
      <Stack gap="sm" className="leanmill-section-body">
        {children}
      </Stack>
    </Box>
  );
}

export function LeanMillPanel({
  state,
  message,
  view = "Start",
  liveMode,
  blueprintDraft,
  setBlueprintDraft,
  blueprintEvent,
  blueprintMessage,
  blueprintRunning,
  actionDraft,
  actionEvent,
  actionMessage,
  actionRunning,
  setActionDraft,
  onPreviewBlueprint,
  onSaveBlueprint,
  onPreviewAction,
  onStartAction,
  onRefresh,
  onPreview,
  onScaffoldArea,
  onNavigateWorkspace
}) {
  const [scaffoldSlug, setScaffoldSlug] = React.useState("");
  const payload = state && typeof state === "object" ? state : {};
  const run = payload.run || {};
  const boundary = payload.boundary || {};
  const claimBoundary = payload.claim_boundary || {};
  const formalizations = payload.formalizations || {};
  const publicReceipts = payload.public_receipts || {};
  const jobs = payload.jobs || {};
  const targetWrites = payload.target_writes || payload.blueprint_writes || {};
  const solverLane = payload.solver_lane || {};
  const typedExits = payload.typed_exits || {};
  const uiState = payload.ui_state || {};
  const leanFiles = Array.isArray(formalizations.lean_files) ? formalizations.lean_files : [];
  const savedTargets = Array.isArray(formalizations.targets)
    ? formalizations.targets
    : Array.isArray(formalizations.blueprints)
    ? formalizations.blueprints
    : [];
  const receiptPaths = Array.isArray(publicReceipts.paths) ? publicReceipts.paths : [];
  const experimentScripts = Array.isArray(publicReceipts.experiment_scripts) ? publicReceipts.experiment_scripts : [];
  const targetHistoryRows = Array.isArray(targetWrites.recent) ? targetWrites.recent : [];
  const jobRows = Array.isArray(jobs.recent) ? jobs.recent : [];
  const typedRows = Array.isArray(typedExits.recent) ? typedExits.recent : [];
  const solverRows = Array.isArray(solverLane.recent) ? solverLane.recent : [];
  // Join a launched job to its proof outcome by target name, so "your attempts" show a verdict — not
  // just "started" (the workbench job result only carries returncode; the verdict lives in the lane).
  const outcomeByTarget = {};
  [...typedRows, ...solverRows].forEach((r) => { if (r && r.target) outcomeByTarget[r.target] = r; });
  const jobVerdict = (row) => {
    const o = row.target_name ? outcomeByTarget[row.target_name] : null;
    if (o) return leanProofVerdict(o);
    if (String(row.status || "").toLowerCase() === "started") return { label: "Running", tone: "gray" };
    if (/fail|error/.test(String(row.status || "").toLowerCase())) return { label: "Did not run", tone: "red" };
    return { label: displayText(row.status || "started"), tone: "gray" };
  };

  const openPreview = (path) => {
    if (path && onPreview && isPreviewableRepoPath(path)) onPreview({ type: "file", value: path });
  };
  const PathButton = ({ path, label = "Open" }) =>
    path && isPreviewableRepoPath(path) ? (
      <Button size="compact-sm" variant="light" onClick={() => openPreview(path)} title={`Preview ${path}`}>
        {label}
      </Button>
    ) : null;

  // Hairline list rows (Linear / Origin scannable-row pattern), not bordered card-soup: name + path/group
  // meta on the left, the open action on the right, separated by a single hairline.
  const FileRows = ({ rows, empty }) =>
    rows.length ? (
      <div className="lm-filelist">
        {rows.map((row) => (
          <div key={row.path || row.name} className="lm-filerow">
            <Box style={{ minWidth: 0 }}>
              <Text fw={560} fz="md" truncate>
                {row.name || row.path}
              </Text>
              <div className="lm-filerow-meta">
                {row.group ? <span>{row.group}</span> : null}
                {row.path ? <Code fz="xs">{row.path}</Code> : null}
              </div>
            </Box>
            <PathButton path={row.path} />
          </div>
        ))}
      </div>
    ) : (
      <Text c="dimmed" fz="sm">
        {empty}
      </Text>
    );

  const Metrics = ({ items }) => (
    <SimpleGrid cols={{ base: 2, sm: items.length > 3 ? 4 : items.length }} spacing="sm">
      {items.map((item) => (
        <Paper key={item.label} withBorder p="sm" radius="sm">
          <Text c="dimmed" fz="xs" tt="uppercase" style={{ letterSpacing: "0.05em" }}>
            {item.label}
          </Text>
          {item.code ? (
            <Code fz="xs" block mt={4}>
              {item.value}
            </Code>
          ) : (
            <Text fw={650} fz="lg">
              {item.value}
            </Text>
          )}
        </Paper>
      ))}
    </SimpleGrid>
  );

  // ---- Start / overview ------------------------------------------------------
  // Organised by JOB, not artifact: the three things people come to LeanMill to do — turn a statement into a
  // proved Lean target, rescue a failing proof, or kernel-check a finished one. Works for math and non-math
  // substrates alike (anything reducible to a Lean target).
  const leanFileCount = formalizations.lean_file_count || leanFiles.length || 0;
  const outcomeCount = (solverLane.result_count || 0) + (typedExits.count || 0);
  const nextLeanMillJobs = [
    {
      id: "formalize",
      title: "Formalize & solve",
      state: "from your notes",
      body: "Turn a statement — a theorem, a spec, an invariant — into a Lean target and let the solver prove it. The common path.",
      action: "Start",
      view: "Run a proof"
    },
    {
      id: "fix",
      title: "Fix a failing proof",
      state: leanFileCount ? `${leanFileCount} Lean file${leanFileCount === 1 ? "" : "s"} on hand` : "drop a .lean",
      body: "Have a Lean file that won't compile, or still carries a sorry? Point the solver at it and it works the gap directly.",
      action: "Open",
      view: "Run a proof"
    },
    {
      id: "ratify",
      title: "Ratify a proof",
      state: outcomeCount ? `${outcomeCount} checked` : "kernel L1·L2·L3",
      body: "Kernel-check a finished proof — compile, axiom allowlist, and anti-laundering gates. Proof, not “looks right”. The thing an LLM can't tell you.",
      action: "See what's verified",
      view: "Proof status"
    }
  ];

  const overview = (
    <Stack gap="lg">
      <Card withBorder={false} shadow="none" bg="transparent" padding={0}>
        <Stack gap="sm">
          {message ? (
            <Text c="dimmed" fz="sm">
              {message}
            </Text>
          ) : null}
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" mt="xs">
            {nextLeanMillJobs.map((job) => (
              <Card key={job.id} withBorder padding="md" style={{ display: "flex", flexDirection: "column", height: "100%", gap: 12 }}>
                <Box>
                  <Badge size="sm" variant="light" mb={6}>
                    {job.state}
                  </Badge>
                  <Title order={4}>{job.title}</Title>
                  <Text c="dimmed" fz="sm" mt={4} style={{ minHeight: "4.7em" }}>
                    {job.body}
                  </Text>
                </Box>
                <Button
                  variant="default"
                  fullWidth
                  style={{ marginTop: "auto" }}
                  onClick={() => onNavigateWorkspace && onNavigateWorkspace("leanmill", job.view)}
                >
                  {job.action}
                </Button>
              </Card>
            ))}
          </SimpleGrid>
          <Group>
            <Button variant="default" onClick={onRefresh} disabled={!liveMode}>
              Refresh LeanMill
            </Button>
          </Group>
        </Stack>
      </Card>

      <Accordion variant="default" radius="md">
        <Accordion.Item value="boundaries">
          <Accordion.Control>Boundaries</Accordion.Control>
          <Accordion.Panel>
            <Stack gap="xs">
              {boundary.target_boundary || boundary.blueprint_boundary ? (
                <Text fz="sm">{boundary.target_boundary || boundary.blueprint_boundary}</Text>
              ) : null}
              <Text fz="sm">{boundary.launch_boundary || "Launch actions write job, log, and result files."}</Text>
              <Stack gap={4}>
                {(claimBoundary.non_claims || []).map((item, index) => (
                  <Text key={`${index}-${item}`} fz="sm" c="dimmed">
                    • {displayMessage(item)}
                  </Text>
                ))}
              </Stack>
            </Stack>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );

  // ---- Draft target ----------------------------------------------------------
  const draft = blueprintDraft || emptyLeanMillBlueprintDraft();
  const setBlueprintField = (field, value) =>
    setBlueprintDraft && setBlueprintDraft({ ...(draft || emptyLeanMillBlueprintDraft()), [field]: value });
  const launchDraft = actionDraft || emptyLeanMillActionDraft();
  const setLaunchField = (field, value) => setActionDraft && setActionDraft({ [field]: value });
  const draftProject = String(draft.project || "").trim();
  const actionJob = actionEvent && actionEvent.job ? actionEvent.job : null;
  const actionPaths = actionJob && actionJob.paths ? actionJob.paths : {};
  const savedTargetOptions = savedTargets.map((row) => row.path).filter(Boolean);
  const leanFileOptions = leanFiles.map((row) => row.path).filter(Boolean);
  const selectedNotesPath =
    launchDraft.notes_path ||
    (blueprintEvent && (blueprintEvent.target_path || blueprintEvent.blueprint_path || blueprintEvent.path)) ||
    "";
  const canSaveDraft = Boolean(
    blueprintEvent && blueprintEvent.preview_sha256 && blueprintEvent.status === "needs_confirmation"
  );
  const fieldDisabled = !liveMode || blueprintRunning;

  const blueprintView = (
    <Stack gap="lg">
      <SectionCard
        eyebrow="Target and notes"
        title="Draft a target"
        description={
          blueprintMessage ||
          "Write the claim you want proved and the notes a later proof attempt should use. Preview first, then save."
        }
      >
        {/* Lead with the claim — it's the point, not the filing metadata. */}
        <Textarea
          label="Target statement"
          description="What LeanMill should try to prove later — the goal, not a finished proof."
          autosize
          minRows={5}
          placeholder="State the theorem or claim you want proved, clearly."
          value={draft.target_statement || ""}
          disabled={fieldDisabled}
          onChange={(e) => setBlueprintField("target_statement", e.currentTarget.value)}
        />
        <Textarea
          label="Research notes"
          description="Definitions, sources, examples, likely blockers — context the prover can draw on later."
          autosize
          minRows={3}
          value={draft.notes || ""}
          disabled={fieldDisabled}
          onChange={(e) => setBlueprintField("notes", e.currentTarget.value)}
        />
        <Textarea
          label="What this doesn't claim yet"
          description="One per line. Example: this is not a proof until a checker accepts it."
          autosize
          minRows={2}
          value={draft.non_claims_text || ""}
          disabled={fieldDisabled}
          onChange={(e) => setBlueprintField("non_claims_text", e.currentTarget.value)}
        />
        {/* Filing metadata — secondary, grouped under a hairline so it doesn't compete with the claim. */}
        <Box className="lm-form-meta">
          <span className="eyebrow">Where it's saved</span>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm" mt="xs">
            <TextInput
              label="Project folder"
              description={`Optional — saves under projects/${(draft.project || "").trim() || "…"}/leanmill/`}
              placeholder="e.g. ai_capex"
              value={draft.project || ""}
              disabled={fieldDisabled}
              onChange={(e) => setBlueprintField("project", e.currentTarget.value)}
            />
            <TextInput
              label="Short name"
              description="Letters, numbers, _ or -. A suffix is added for you."
              placeholder="mathd_algebra_182"
              value={draft.slug || ""}
              disabled={fieldDisabled}
              onChange={(e) => setBlueprintField("slug", e.currentTarget.value)}
            />
            <TextInput
              label="Title"
              description="Human-readable name in the saved markdown."
              placeholder="Algebra target notes"
              value={draft.title || ""}
              disabled={fieldDisabled}
              onChange={(e) => setBlueprintField("title", e.currentTarget.value)}
            />
          </SimpleGrid>
        </Box>
        <Alert variant="light" color="gray" radius="md" title="What saving does">
          Saving stores the target, your research notes, and a saved-history record in this project's
          LeanMill folder. It does not launch a proof attempt — previewing changes nothing.
        </Alert>
        <Group>
          <Button variant="default" disabled={fieldDisabled} onClick={onPreviewBlueprint}>
            {blueprintRunning ? "Working" : "Preview"}
          </Button>
          <Button
            className={blueprintRunning ? "is-busy" : undefined}
            disabled={fieldDisabled || !canSaveDraft}
            onClick={onSaveBlueprint}
            title={canSaveDraft ? "Save the previewed target and notes" : "Preview the write before saving"}
          >
            {blueprintRunning ? "Saving" : "Save notes and target"}
          </Button>
        </Group>
      </SectionCard>

      {blueprintEvent ? (
        <SectionCard
          eyebrow={displayText(blueprintEvent.status || "preview")}
          title={blueprintEvent.accepted ? "Target saved" : "Save preview"}
        >
          <Metrics
            items={[
              { label: "Target and notes", value: blueprintEvent.target_path || blueprintEvent.blueprint_path || blueprintEvent.path || "not set", code: true },
              { label: "History", value: blueprintEvent.saved_history_path || blueprintEvent.receipt_path || "not set", code: true },
              { label: "Latest", value: blueprintEvent.latest_history_path || blueprintEvent.latest || "not set", code: true },
              { label: "Changed", value: blueprintEvent.no_change ? "no" : "yes" }
            ]}
          />
          {blueprintEvent.target_text || blueprintEvent.blueprint_text ? (
            <Code block fz="xs">
              {blueprintEvent.target_text || blueprintEvent.blueprint_text}
            </Code>
          ) : null}
          <Group>
            <PathButton path={blueprintEvent.target_path || blueprintEvent.blueprint_path || blueprintEvent.path} label="Open target and notes" />
            <PathButton path={blueprintEvent.latest_history_path || blueprintEvent.latest} label="Open saved history" />
          </Group>
        </SectionCard>
      ) : null}

      {targetHistoryRows.length ? (
        <SectionCard title="Recent saved targets">
          <Stack gap="xs">
            {targetHistoryRows.map((row) => (
              <Paper key={`${row.applied_at}-${row.slug}`} withBorder p="sm" radius="sm">
                <Group justify="space-between">
                  <Text fw={550} fz="sm">
                    {row.title || row.slug || "saved target"}
                  </Text>
                  <Badge size="sm" variant="light" color={row.content_changed ? "indigo" : "gray"}>
                    {row.content_changed ? "changed" : "unchanged"}
                  </Badge>
                </Group>
                <Code fz="xs">{row.target_path || row.blueprint_path || ""}</Code>
              </Paper>
            ))}
          </Stack>
        </SectionCard>
      ) : null}
    </Stack>
  );

  // ---- Run a proof -----------------------------------------------------------
  // Launching a proof is a different job from drafting a target, so it gets its own screen.
  const runView = (
    <Stack gap="lg">
      <SectionCard
        eyebrow="From notes"
        title="Turn a saved target into a proof attempt"
        description={
          actionMessage ||
          "Pick a saved target-and-notes file. The solver runs in the background; its outcome shows on Proof status."
        }
      >
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          <NativeSelect
            label="Saved target"
            value={selectedNotesPath}
            disabled={!liveMode || actionRunning}
            onChange={(e) => setLaunchField("notes_path", e.currentTarget.value)}
            data={[{ value: "", label: "Choose a saved target" }, ...savedTargetOptions.map((p) => ({ value: p, label: p }))]}
          />
          <TextInput
            label="Project"
            placeholder="optional project"
            value={launchDraft.project || ""}
            disabled={!liveMode || actionRunning}
            onChange={(e) => setLaunchField("project", e.currentTarget.value)}
          />
        </SimpleGrid>
        <Group>
          <Button variant="default" disabled={!liveMode || actionRunning || !selectedNotesPath} onClick={() => onPreviewAction && onPreviewAction("autoformalize", false)}>
            {actionRunning ? "Working" : "Preview"}
          </Button>
          <Button color="indigo" className={actionRunning ? "is-busy" : undefined} disabled={!liveMode || actionRunning || !selectedNotesPath} onClick={() => onStartAction && onStartAction("autoformalize", true)}>
            {actionRunning ? "Starting" : "Run from notes"}
          </Button>
        </Group>
      </SectionCard>

      <SectionCard
        eyebrow="From a Lean file"
        title="Solve a named target in a Lean file"
        description="Use this when you already have a Lean file with a named theorem to prove. The solver records the outcome."
      >
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <TextInput
            label="Target name"
            placeholder="my_theorem"
            value={launchDraft.target_name || ""}
            disabled={!liveMode || actionRunning}
            onChange={(e) => setLaunchField("target_name", e.currentTarget.value)}
          />
          <NativeSelect
            label="Lean file"
            value={launchDraft.source_file || ""}
            disabled={!liveMode || actionRunning}
            onChange={(e) => setLaunchField("source_file", e.currentTarget.value)}
            data={[{ value: "", label: "Choose Lean file" }, ...leanFileOptions.map((p) => ({ value: p, label: p }))]}
          />
          <NativeSelect
            label="How hard to search"
            value={launchDraft.mode || "dag_search"}
            disabled={!liveMode || actionRunning}
            onChange={(e) => setLaunchField("mode", e.currentTarget.value)}
            data={[
              { value: "dag_search", label: "Deep search" },
              { value: "cascade", label: "Fast cascade" }
            ]}
          />
        </SimpleGrid>
        <Group>
          <Button variant="default" disabled={!liveMode || actionRunning || !launchDraft.target_name || !launchDraft.source_file} onClick={() => onPreviewAction && onPreviewAction("adhoc", false)}>
            {actionRunning ? "Working" : "Preview"}
          </Button>
          <Button color="indigo" className={actionRunning ? "is-busy" : undefined} disabled={!liveMode || actionRunning || !launchDraft.target_name || !launchDraft.source_file} onClick={() => onStartAction && onStartAction("adhoc", true)}>
            {actionRunning ? "Starting" : "Run solver"}
          </Button>
        </Group>
      </SectionCard>

      {actionJob ? (
        <SectionCard eyebrow={displayText(actionEvent.status || actionJob.status || "job")} title={actionEvent.accepted ? "Attempt started" : "Attempt preview"}>
          <Text c="dimmed" fz="sm">
            {actionEvent.accepted
              ? "Running in the background — the outcome will appear on Proof status when it finishes."
              : "This is a preview. Confirm to start the attempt."}
          </Text>
          <Group>
            <PathButton path={actionPaths.result} label="Open result" />
            <PathButton path={actionPaths.stdout} label="Open log" />
          </Group>
        </SectionCard>
      ) : null}
    </Stack>
  );

  // ---- Proof files -----------------------------------------------------------
  const projectAreas = payload.project_areas || {};
  const areaRows = Array.isArray(projectAreas.areas) ? projectAreas.areas : [];

  const formalizationView = (
    <Stack gap="lg">
      <SectionCard
        eyebrow="Project work"
        title={projectAreas.label || "Your proof workspaces"}
        description={projectAreas.note || "Proof work that lives under a selected research project."}
      >
        {areaRows.length ? (
          <Stack gap="xs">
            {areaRows.map((area) => (
              <Paper key={area.project} withBorder p="sm" radius="sm">
                <Group justify="space-between" wrap="nowrap" align="center">
                  <Box style={{ minWidth: 0 }}>
                    <Text fw={600} fz="sm">
                      {area.project}
                    </Text>
                    <Group gap={6} mt={4}>
                      <Badge size="sm" variant="light">{area.target_count || 0} targets</Badge>
                      <Badge size="sm" variant="light" color="grape">{area.lean_file_count || 0} Lean</Badge>
                      <Badge size="sm" variant="light" color="teal">{area.job_count || 0} jobs</Badge>
                    </Group>
                    <Code fz="xs" mt={4} block>
                      {area.root || ""}
                    </Code>
                  </Box>
                  {(area.targets || []).length ? <PathButton path={area.targets[0]} label="Open target" /> : null}
                </Group>
              </Paper>
            ))}
          </Stack>
        ) : (
          <Alert variant="light" color="gray" radius="md">
            No project has a LeanMill area yet. Scaffold one, or save a target with a project selected, to create
            projects/&lt;project&gt;/leanmill/.
          </Alert>
        )}
        {onScaffoldArea ? (
          <Box>
            <span className="lm-field-label" style={{ display: "block", marginBottom: 6 }}>Create a project area</span>
            <Group align="center" gap="sm" wrap="nowrap">
              <TextInput
                placeholder="project slug"
                value={scaffoldSlug}
                onChange={(e) => setScaffoldSlug(e.currentTarget.value)}
                style={{ flex: 1 }}
              />
              <Button
                disabled={!liveMode || !scaffoldSlug.trim()}
                onClick={() => onScaffoldArea(scaffoldSlug.trim())}
                title={liveMode ? "Create projects/<slug>/leanmill" : "Start the workbench server first"}
              >
                Create area
              </Button>
            </Group>
          </Box>
        ) : null}
      </SectionCard>

      <SectionCard
        eyebrow="Examples"
        title={formalizations.label || "Example proofs"}
        description={formalizations.note || "A read-only library of example targets and Lean files to learn from — not your project work."}
      >
        <FileRows rows={savedTargets} empty="No example targets found." />
        <Accordion variant="default" radius="md">
          <Accordion.Item value="lean-files">
            <Accordion.Control>Example Lean files</Accordion.Control>
            <Accordion.Panel>
              <FileRows rows={leanFiles} empty="No Lean files found." />
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>
        {formalizations.root ? <Code fz="xs">{formalizations.root}</Code> : null}
      </SectionCard>
    </Stack>
  );

  // ---- Proof status ----------------------------------------------------------
  const receiptsView = (
    <Stack gap="lg">
      <SectionCard
        eyebrow="Saved history"
        title="Review attempts"
        description="An attempt is only guidance until the result, the Lean check, and the saved record all agree."
      >
        <Metrics
          items={[
            { label: "Proof attempts", value: String(solverLane.result_count || 0) },
            { label: "Results", value: String(typedExits.count || 0) },
            { label: "Open targets", value: String((uiState.lane_b || {}).targets || 0) },
            { label: "Verified", value: String((payload.closure_certificates || {}).recent_count || 0) }
          ]}
        />
        <Accordion variant="default" radius="md">
          <Accordion.Item value="history">
            <Accordion.Control>Saved-history files</Accordion.Control>
            <Accordion.Panel>
              <FileRows rows={receiptPaths.map((p) => ({ path: p }))} empty="No saved-history files found." />
            </Accordion.Panel>
          </Accordion.Item>
          {experimentScripts.length ? (
            <Accordion.Item value="scripts">
              <Accordion.Control>Re-runnable scripts</Accordion.Control>
              <Accordion.Panel>
                <FileRows rows={experimentScripts.map((p) => ({ path: p }))} empty="" />
              </Accordion.Panel>
            </Accordion.Item>
          ) : null}
        </Accordion>
      </SectionCard>

      {typedRows.length ? (
        <SectionCard title="Recent outcomes">
          <Stack gap="xs">
            {typedRows.map((row) => {
              const v = leanProofVerdict(row);
              const t = humanizeTarget(row.target);
              return (
                <div key={row.target || row.next_lever} className="lm-outcome">
                  <div className="lm-outcome-head">
                    <Box style={{ minWidth: 0 }}>
                      <Group gap={7} align="baseline" wrap="nowrap">
                        {t.kind ? <Badge size="sm" variant="light" color="gray">{t.kind}</Badge> : null}
                        <Code fz="sm">{t.name}</Code>
                      </Group>
                      {(v.gap || v.next) ? (
                        <Text c="dimmed" fz="xs" mt={4}>
                          {v.gap}{v.gap && v.next ? " " : ""}{v.next ? `Next: ${v.next}.` : ""}
                        </Text>
                      ) : null}
                    </Box>
                    <Badge size="sm" variant="light" color={v.tone}>
                      {v.label}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </Stack>
          <PathButton path={typedExits.path} label="Open result file" />
        </SectionCard>
      ) : null}

      {jobRows.length ? (
        <SectionCard eyebrow="Your attempts" title="Proof attempts you launched">
          <Stack gap="xs">
            {jobRows.map((row) => {
              const v = jobVerdict(row);
              return (
                <Paper key={row.job_path || `${row.created_at}-${row.action}`} withBorder p="sm" radius="sm">
                  <Group justify="space-between">
                    <Text fw={550} fz="sm">
                      {row.target_name || row.label || displayText(row.action || "attempt")}
                    </Text>
                    <Badge size="sm" variant="light" color={v.tone}>
                      {v.label}
                    </Badge>
                  </Group>
                  {v.gap ? (
                    <Text c="dimmed" fz="xs" mt={4}>{v.gap}</Text>
                  ) : null}
                  <Group gap="xs" mt={6}>
                    <PathButton path={row.result_path} label="Open result" />
                    <PathButton path={row.stdout_path} label="Open log" />
                  </Group>
                </Paper>
              );
            })}
          </Stack>
        </SectionCard>
      ) : null}

      {solverRows.length ? (
        <SectionCard eyebrow="Other LeanMill runs" title="Proofs from across LeanMill">
          <div className="lm-outcome-list">
            {solverRows.map((row) => {
              const v = leanProofVerdict(row);
              const t = humanizeTarget(row.target);
              return (
                <div key={row.target || row.provider} className="lm-outcome">
                  <div className="lm-outcome-head">
                    <Box style={{ minWidth: 0 }}>
                      <Group gap={7} align="baseline" wrap="nowrap">
                        {t.kind ? <Badge size="sm" variant="light" color="gray">{t.kind}</Badge> : null}
                        <Code fz="sm">{t.name}</Code>
                      </Group>
                      {row.provider ? (
                        <Text c="dimmed" fz="xs" mt={4}>{`Solved with ${displayText(row.provider)}.`}</Text>
                      ) : null}
                    </Box>
                    <Badge size="sm" variant="light" color={v.tone}>{v.label}</Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </SectionCard>
      ) : null}
    </Stack>
  );

  const normalizedView = normalizeLeanMillView(view);
  const body =
    normalizedView === "Draft target"
      ? blueprintView
      : normalizedView === "Run a proof"
      ? runView
      : normalizedView === "Proof files"
      ? formalizationView
      : normalizedView === "Proof status"
      ? receiptsView
      : overview;

  return (
    <Box aria-label="LeanMill section">
      {run.active ? (
        <div className="run-progress-banner" aria-label="LeanMill run in progress">
          <span className="run-progress-dot" aria-hidden="true" />
          <div className="run-progress-copy">
            <strong>LeanMill is running</strong>
            <span>
              {run.worker_count} {run.worker_count === 1 ? "worker" : "workers"} active — proofs are being attempted right now. Refresh to update.
            </span>
          </div>
        </div>
      ) : null}
      {body}
    </Box>
  );
}
