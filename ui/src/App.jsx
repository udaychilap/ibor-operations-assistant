import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [ingestion, setIngestion] = useState(null);
  const [recon, setRecon] = useState(null);
  const [breaks, setBreaks] = useState([]);
  const [loading, setLoading] = useState("");

  // =========================================================
  // AI Investigation
  // =========================================================

  const [selectedBreak, setSelectedBreak] = useState(null);
  const [aiResult, setAiResult] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  // =========================================================
  // AI Chat
  // =========================================================

  const [chatScope, setChatScope] = useState("selected");
  const [chatQuestion, setChatQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  // =========================================================
  // Reset Demo
  // =========================================================

  async function resetDemo() {
    try {
      setLoading("reset");

      const response = await fetch(`${API}/demo/reset`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      await response.json();

      setIngestion(null);
      setRecon(null);
      setBreaks([]);

      // Reset AI state
      setSelectedBreak(null);
      setAiResult(null);

      // Reset chat
      setChatMessages([]);
      setChatQuestion("");
      setChatScope("selected");
    } catch (error) {
      alert(`Demo reset failed: ${error.message}`);
    } finally {
      setLoading("");
    }
  }

  // =========================================================
  // Ingestion
  // =========================================================

  async function ingestData() {
    try {
      setLoading("ingest");

      const response = await fetch(`${API}/ingest`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      setIngestion(data);
    } catch (error) {
      alert(`Ingestion failed: ${error.message}`);
    } finally {
      setLoading("");
    }
  }

  // =========================================================
  // Reconciliation
  // =========================================================

  async function runRecon() {
    try {
      setLoading("recon");

      const response = await fetch(`${API}/reconcile`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      setRecon(data);

      setSelectedBreak(null);
      setAiResult(null);

      setChatMessages([]);
      setChatQuestion("");

      await loadBreaks();
    } catch (error) {
      alert(`Reconciliation failed: ${error.message}`);
    } finally {
      setLoading("");
    }
  }

  // =========================================================
  // Load Reconciliation Breaks
  // =========================================================

  async function loadBreaks() {
    try {
      const response = await fetch(`${API}/recon/breaks`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      setBreaks(
        Array.isArray(data)
          ? data
          : data.breaks || []
      );
    } catch (error) {
      console.error(
        "Unable to load breaks:",
        error
      );
    }
  }

  // =========================================================
  // Existing AI Investigation
  // =========================================================

  async function investigateWithAI(item) {
    try {
      setSelectedBreak(item);
      setAiResult(null);
      setAiLoading(true);

      const response = await fetch(
        `${API}/assistant/investigate/${item.recon_id}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      setAiResult(data);

      /*
       * Also put investigation result into chat.
       * This lets the operator continue asking follow-up questions.
       */
      if (data.ai_explanation) {
        setChatMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: data.ai_explanation,
          },
        ]);
      }
    } catch (error) {
      alert(
        `AI investigation failed: ${error.message}`
      );
    } finally {
      setAiLoading(false);
    }
  }

  // =========================================================
  // Select Break
  // =========================================================

  function selectBreak(item) {
    const changingBreak =
      selectedBreak?.recon_id !== item.recon_id;

    setSelectedBreak(item);
    setAiResult(null);

    /*
     * Selected recon mode is the natural default
     * whenever the operator clicks a break.
     */
    setChatScope("selected");

    /*
     * Prevent chat from one break being confused
     * with another break.
     */
    if (changingBreak) {
      setChatMessages([]);
    }
  }

  // =========================================================
  // AI Chat
  // =========================================================

  async function askAI(
    questionOverride = null
  ) {
    const question =
      questionOverride?.trim() ||
      chatQuestion.trim();

    if (!question) {
      return;
    }

    if (
      chatScope === "selected" &&
      !selectedBreak
    ) {
      alert(
        "Select a reconciliation break first, or switch to All Recons."
      );

      return;
    }

    const userMessage = {
      role: "user",
      content: question,
    };

    const newHistory = [
      ...chatMessages,
      userMessage,
    ];

    setChatMessages(newHistory);
    setChatQuestion("");
    setChatLoading(true);

    try {
      /*
       * Backend contract:
       *
       * POST /assistant/chat
       *
       * {
       *   question: "...",
       *   scope: "selected" | "all",
       *   recon_id: 26 | null,
       *   business_date: "...",
       *   history: [...]
       * }
       */

      const response = await fetch(
        `${API}/assistant/chat`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            question,
            scope: chatScope,

            recon_id:
              chatScope === "selected"
                ? selectedBreak?.recon_id
                : null,

            business_date:
              recon?.business_date || null,

            history: newHistory,
          }),
        }
      );

      if (!response.ok) {
        let errorMessage =
          `HTTP ${response.status}`;

        try {
          const errorData =
            await response.json();

          errorMessage =
            errorData.detail ||
            errorData.message ||
            errorMessage;
        } catch {
          // Ignore JSON parsing failure
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();

      /*
       * Support a few likely response names
       * while we're developing the API.
       */
      const answer =
        data.answer ||
        data.ai_explanation ||
        data.response ||
        "The assistant returned no explanation.";

      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: answer,

          model:
            data.model || null,

          evidence_count:
            data.evidence_count ??
            null,
        },
      ]);
    } catch (error) {
      setChatMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            `Unable to answer the question.\n\n${error.message}`,
          error: true,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  // =========================================================
  // Chat Keyboard Handling
  // =========================================================

  function handleChatKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      if (!chatLoading) {
        askAI();
      }
    }
  }

  // =========================================================
  // Clear Chat
  // =========================================================

  function clearChat() {
    setChatMessages([]);
    setChatQuestion("");
  }

  // =========================================================
  // Recon Count
  // =========================================================

  function reconCount(status) {
    if (!recon?.summary) {
      return 0;
    }

    const item = recon.summary.find(
      (row) =>
        row.recon_status === status
    );

    return item?.count || 0;
  }

  // =========================================================
  // Render
  // =========================================================

  return (
    <div className="app">
      {/* =================================================== */}
      {/* Header                                              */}
      {/* =================================================== */}

      <header>
        <div>
          <h1>
            IBOR Operations Assistant
          </h1>

          <p>
            Data Ingestion & Transaction
            Reconciliation
          </p>
        </div>

        <span className="healthy">
          ● IBOR ONLINE
        </span>
      </header>

      {/* =================================================== */}
      {/* Actions                                             */}
      {/* =================================================== */}

      <section className="actions">
        <button
          onClick={resetDemo}
          disabled={loading}
          className="resetButton"
        >
          {loading === "reset"
            ? "Resetting..."
            : "Reset Demo"}
        </button>

        <button
          onClick={ingestData}
          disabled={loading}
        >
          {loading === "ingest"
            ? "Ingesting..."
            : "1. Ingest Transaction Feed"}
        </button>

        <button
          onClick={runRecon}
          disabled={
            loading ||
            !ingestion
          }
          className="secondary"
        >
          {loading === "recon"
            ? "Running..."
            : "2. Run Transaction Recon"}
        </button>
      </section>

      {/* =================================================== */}
      {/* Ingestion Status                                    */}
      {/* =================================================== */}

      <section>
        <h2>Ingestion Status</h2>

        <div className="cards">
          <Metric
            label="Input Transactions"
            value={
              ingestion?.input_count ??
              0
            }
          />

          <Metric
            label="Successfully Loaded"
            value={
              ingestion?.success_count ??
              0
            }
          />

          <Metric
            label="Rejected"
            value={
              ingestion?.reject_count ??
              0
            }
          />

          <Metric
            label="Load Status"
            value={
              ingestion?.status ??
              "NOT RUN"
            }
          />
        </div>

        {ingestion && (
          <div className="runInfo">
            <strong>Run ID:</strong>{" "}
            {ingestion.run_id}
          </div>
        )}
      </section>

      {/* =================================================== */}
      {/* Transaction Reconciliation                          */}
      {/* =================================================== */}

      <section>
        <div className="sectionTitle">
          <h2>
            Transaction Reconciliation
          </h2>

          {recon && (
            <span>
              Business Date:{" "}
              {recon.business_date}
            </span>
          )}
        </div>

        <div className="cards">
          <Metric
            label="Paired"
            value={reconCount("PAIRED")}
          />

          <Metric
            label="UNPAIR-EXT"
            value={reconCount(
              "UNPAIR-EXT"
            )}
          />

          <Metric
            label="UNPAIR-INT"
            value={reconCount(
              "UNPAIR-INT"
            )}
          />

          <Metric
            label="Mismatch"
            value={reconCount(
              "MISMATCH"
            )}
          />
        </div>
      </section>

      {/* =================================================== */}
      {/* Reconciliation Exceptions                           */}
      {/* =================================================== */}

      <section>
        <div className="sectionTitle">
          <h2>
            Reconciliation Exceptions
          </h2>

          <button
            className="smallButton"
            onClick={loadBreaks}
          >
            Refresh
          </button>
        </div>

        {breaks.length === 0 ? (
          <div className="successBox">
            ✓ No reconciliation
            exceptions detected.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Recon ID</th>
                <th>Account</th>
                <th>Security</th>
                <th>Status</th>
                <th>Reason</th>
                <th>
                  AI Investigation
                </th>
              </tr>
            </thead>

            <tbody>
              {breaks.map(
                (item, index) => (
                  <tr
                    key={
                      item.recon_id ||
                      index
                    }
                    className={
                      selectedBreak?.recon_id ===
                      item.recon_id
                        ? "selectedRow"
                        : "clickableRow"
                    }
                    onClick={() =>
                      selectBreak(item)
                    }
                  >
                    <td>
                      {item.recon_id ||
                        "-"}
                    </td>

                    <td>
                      {item.account_id ||
                        "-"}
                    </td>

                    <td>
                      {item.security_id ||
                        item.symbol ||
                        "-"}
                    </td>

                    <td>
                      <span className="breakStatus">
                        {item.recon_status ||
                          item.status ||
                          "BREAK"}
                      </span>
                    </td>

                    <td>
                      {item.reason ||
                        item.break_reason ||
                        "-"}
                    </td>

                    <td>
                      <button
                        className="smallButton"
                        onClick={(
                          event
                        ) => {
                          event.stopPropagation();

                          investigateWithAI(
                            item
                          );
                        }}
                        disabled={
                          aiLoading
                        }
                      >
                        {aiLoading &&
                        selectedBreak?.recon_id ===
                          item.recon_id
                          ? "Investigating..."
                          : "Investigate"}
                      </button>
                    </td>
                  </tr>
                )
              )}
            </tbody>
          </table>
        )}
      </section>

      {/* =================================================== */}
      {/* AI Operations Assistant                             */}
      {/* =================================================== */}

      <section className="assistantSection">
        <div className="sectionTitle">
          <div>
            <h2>
              AI Recon Assistant
            </h2>

            <p className="assistantSubtitle">
              Ask questions about
              reconciliation exceptions,
              failures and operational
              evidence
            </p>
          </div>

          {selectedBreak && (
            <span className="selectedBreakBadge">
              #
              {
                selectedBreak.recon_id
              }{" "}
              ·{" "}
              {
                selectedBreak.recon_status
              }
            </span>
          )}
        </div>

        {/* =============================================== */}
        {/* Scope                                           */}
        {/* =============================================== */}

        <div className="chatScope">
          <button
            className={
              chatScope === "selected"
                ? "scopeButton active"
                : "scopeButton"
            }
            onClick={() =>
              setChatScope(
                "selected"
              )
            }
            disabled={
              !selectedBreak
            }
          >
            Selected Recon
          </button>

          <button
            className={
              chatScope === "all"
                ? "scopeButton active"
                : "scopeButton"
            }
            onClick={() =>
              setChatScope("all")
            }
          >
            All Recons
          </button>
        </div>

        <div className="assistantLayout">
          {/* ============================================= */}
          {/* Left Side: Context                            */}
          {/* ============================================= */}

          <div className="breakContext">
            <div className="breakContextTitle">
              <h3>
                {chatScope ===
                "selected"
                  ? "Selected Break"
                  : "Reconciliation Run"}
              </h3>

              {selectedBreak &&
                chatScope ===
                  "selected" && (
                  <span className="breakTypeBadge">
                    {selectedBreak.recon_status}
                  </span>
                )}
            </div>

            {chatScope ===
            "selected" ? (
              selectedBreak ? (
                <>
                  <div className="contextGrid">
                    <ContextItem
                      label="Recon ID"
                      value={
                        selectedBreak.recon_id
                      }
                    />

                    <ContextItem
                      label="Status"
                      value={
                        selectedBreak.recon_status
                      }
                    />

                    <ContextItem
                      label="Account"
                      value={
                        selectedBreak.account_id
                      }
                    />

                    <ContextItem
                      label="Security"
                      value={
                        selectedBreak.security_id ||
                        selectedBreak.symbol
                      }
                    />
                  </div>

                  {(selectedBreak.reason ||
                    selectedBreak.break_reason) && (
                    <div className="contextItem">
                      <span>
                        Break Reason
                      </span>

                      <strong>
                        {selectedBreak.reason ||
                          selectedBreak.break_reason}
                      </strong>
                    </div>
                  )}

                  <div className="contextActions">
                    <button
                      onClick={() =>
                        investigateWithAI(
                          selectedBreak
                        )
                      }
                      disabled={
                        aiLoading
                      }
                    >
                      {aiLoading
                        ? "AI Investigating..."
                        : "Investigate with AI"}
                    </button>
                  </div>
                </>
              ) : (
                <div className="assistantEmpty">
                  Select a
                  reconciliation
                  exception from the
                  table above.
                </div>
              )
            ) : (
              <>
                <div className="contextGrid">
                  <ContextItem
                    label="Business Date"
                    value={
                      recon?.business_date ||
                      "-"
                    }
                  />

                  <ContextItem
                    label="Total Breaks"
                    value={
                      breaks.length
                    }
                  />

                  <ContextItem
                    label="UNPAIR-EXT"
                    value={reconCount(
                      "UNPAIR-EXT"
                    )}
                  />

                  <ContextItem
                    label="UNPAIR-INT"
                    value={reconCount(
                      "UNPAIR-INT"
                    )}
                  />

                  <ContextItem
                    label="Mismatch"
                    value={reconCount(
                      "MISMATCH"
                    )}
                  />

                  <ContextItem
                    label="Paired"
                    value={reconCount(
                      "PAIRED"
                    )}
                  />
                </div>
              </>
            )}

            {/* =========================================== */}
            {/* Quick Questions                             */}
            {/* =========================================== */}

            <div className="quickQuestions">
              <div className="quickQuestionsLabel">
                Quick Questions
              </div>

              <div className="quickQuestionButtons">
                {chatScope ===
                "selected" ? (
                  <>
                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Explain this reconciliation break in simple operational terms."
                        )
                      }
                      disabled={
                        !selectedBreak ||
                        chatLoading
                      }
                    >
                      Explain Break
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "What is the root cause of this reconciliation failure?"
                        )
                      }
                      disabled={
                        !selectedBreak ||
                        chatLoading
                      }
                    >
                      Root Cause
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "What steps should operations take to resolve this reconciliation break?"
                        )
                      }
                      disabled={
                        !selectedBreak ||
                        chatLoading
                      }
                    >
                      How to Resolve
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Show the internal and external evidence associated with this reconciliation break."
                        )
                      }
                      disabled={
                        !selectedBreak ||
                        chatLoading
                      }
                    >
                      Show Evidence
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Are there similar reconciliation breaks in this run?"
                        )
                      }
                      disabled={
                        !selectedBreak ||
                        chatLoading
                      }
                    >
                      Similar Breaks
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Summarize the reconciliation failures for this business date."
                        )
                      }
                      disabled={
                        chatLoading
                      }
                    >
                      Failure Summary
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "What are the major reconciliation break categories in this run?"
                        )
                      }
                      disabled={
                        chatLoading
                      }
                    >
                      Break Categories
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Which accounts have reconciliation failures?"
                        )
                      }
                      disabled={
                        chatLoading
                      }
                    >
                      Failed Accounts
                    </button>

                    <button
                      className="quickQuestionButton"
                      onClick={() =>
                        askAI(
                          "Which reconciliation breaks should operations investigate first and why?"
                        )
                      }
                      disabled={
                        chatLoading
                      }
                    >
                      Operational Review
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* ============================================= */}
          {/* Right Side: Chat                              */}
          {/* ============================================= */}

          <div className="chatPanel">
            <div className="chatHeader">
              <div>
                <div className="chatHeaderTitle">
                  AI Operations Chat
                </div>

                <div className="assistantSubtitle">
                  {chatScope ===
                  "selected"
                    ? selectedBreak
                      ? `Context: Recon #${selectedBreak.recon_id}`
                      : "No reconciliation break selected"
                    : `Context: All reconciliation results${
                        recon?.business_date
                          ? ` · ${recon.business_date}`
                          : ""
                      }`}
                </div>
              </div>

              <div>
                <span className="chatHeaderStatus">
                  ● Ready
                </span>
              </div>
            </div>

            {/* =========================================== */}
            {/* Messages                                    */}
            {/* =========================================== */}

            <div className="chatMessages">
              {chatMessages.length ===
                0 &&
              !chatLoading ? (
                <div className="chatEmpty">
                  <div className="chatEmptyIcon">
                    ◈
                  </div>

                  <h3>
                    Ask about the
                    reconciliation
                  </h3>

                  <p>
                    Ask the assistant
                    about root cause,
                    matching evidence,
                    transaction
                    failures, account
                    breaks or operational
                    resolution.
                  </p>
                </div>
              ) : (
                <>
                  {chatMessages.map(
                    (
                      message,
                      index
                    ) => (
                      <ChatMessage
                        key={index}
                        message={
                          message
                        }
                      />
                    )
                  )}

                  {chatLoading && (
                    <div className="chatMessage assistant">
                      <div className="chatBubble">
                        <span className="chatRole">
                          AI Recon
                          Assistant
                        </span>

                        <div className="chatThinking">
                          Analyzing
                          reconciliation
                          evidence
                          <span className="thinkingDot" />
                          <span className="thinkingDot" />
                          <span className="thinkingDot" />
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* =========================================== */}
            {/* Input                                       */}
            {/* =========================================== */}

            <div className="chatInputArea">
              <textarea
                className="chatInput"
                rows="2"
                placeholder={
                  chatScope ===
                  "selected"
                    ? "Ask about this reconciliation break..."
                    : "Ask about all reconciliation failures..."
                }
                value={
                  chatQuestion
                }
                onChange={(event) =>
                  setChatQuestion(
                    event.target.value
                  )
                }
                onKeyDown={
                  handleChatKeyDown
                }
                disabled={
                  chatLoading
                }
              />

              <button
                className="chatSendButton"
                onClick={() =>
                  askAI()
                }
                disabled={
                  chatLoading ||
                  !chatQuestion.trim() ||
                  (chatScope ===
                    "selected" &&
                    !selectedBreak)
                }
              >
                {chatLoading
                  ? "Thinking..."
                  : "Ask AI"}
              </button>
            </div>

            {chatMessages.length >
              0 && (
              <div
                style={{
                  padding:
                    "0 18px 14px",
                  textAlign:
                    "right",
                }}
              >
                <button
                  className="quickQuestionButton"
                  onClick={
                    clearChat
                  }
                  disabled={
                    chatLoading
                  }
                >
                  Clear Conversation
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* =================================================== */}
      {/* Existing Investigation Result                       */}
      {/* =================================================== */}

      {selectedBreak &&
        aiResult && (
          <section>
            <div className="sectionTitle">
              <h2>
                Investigation Detail
              </h2>

              <span className="selectedBreakBadge">
                Recon #
                {
                  selectedBreak.recon_id
                }
              </span>
            </div>

            <div className="assistantResponse">
              <div className="aiHeader">
                <strong>
                  AI Analysis
                </strong>

                <span>
                  {aiResult.model ||
                    "AI Assistant"}
                </span>
              </div>

              <div className="aiExplanation">
                {
                  aiResult.ai_explanation
                }
              </div>
            </div>
          </section>
        )}

      {/* =================================================== */}
      {/* Process Flow                                        */}
      {/* =================================================== */}

      <section>
        <h2>Process Flow</h2>

        <div className="flow">
          <FlowStep
            name="External Feed"
            active={true}
          />

          <span>→</span>

          <FlowStep
            name="IBOR Load"
            active={!!ingestion}
          />

          <span>→</span>

          <FlowStep
            name="Transaction Recon"
            active={!!recon}
          />

          <span>→</span>

          <FlowStep
            name="Position Recon"
            active={false}
          />

          <span>→</span>

          <FlowStep
            name="BOD / Promotion"
            active={false}
          />
        </div>
      </section>

      {/* =================================================== */}
      {/* API Response                                        */}
      {/* =================================================== */}

      {(ingestion ||
        recon) && (
        <section>
          <h2>
            API Response
          </h2>

          <pre>
            {JSON.stringify(
              {
                ingestion,
                reconciliation:
                  recon,
              },
              null,
              2
            )}
          </pre>
        </section>
      )}
    </div>
  );
}

/* ========================================================= */
/* Helper Components                                         */
/* ========================================================= */

function Metric({
  label,
  value,
}) {
  return (
    <div className="metric">
      <div className="metricLabel">
        {label}
      </div>

      <div className="metricValue">
        {value}
      </div>
    </div>
  );
}

function FlowStep({
  name,
  active,
}) {
  return (
    <div
      className={
        active
          ? "flowStep active"
          : "flowStep"
      }
    >
      {name}
    </div>
  );
}

function ContextItem({
  label,
  value,
}) {
  return (
    <div className="contextItem">
      <span>{label}</span>

      <strong>
        {value ?? "-"}
      </strong>
    </div>
  );
}

function ChatMessage({
  message,
}) {
  return (
    <div
      className={`chatMessage ${message.role}`}
    >
      <div className="chatBubble">
        <span className="chatRole">
          {message.role ===
          "user"
            ? "You"
            : "AI Recon Assistant"}
        </span>

        {message.content}

        {message.evidence_count !==
          null &&
          message.evidence_count !==
            undefined && (
            <div
              style={{
                marginTop:
                  "10px",
                fontSize:
                  "11px",
                opacity: 0.65,
              }}
            >
              Evidence records:{" "}
              {
                message.evidence_count
              }
            </div>
          )}
      </div>
    </div>
  );
}