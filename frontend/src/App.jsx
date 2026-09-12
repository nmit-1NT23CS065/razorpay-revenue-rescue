import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [analysis, setAnalysis] = useState(null);
  const [recoveryPlan, setRecoveryPlan] = useState(null);
  const [execution, setExecution] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);

  const money = (value) =>
    `₹${Number(value || 0).toLocaleString("en-IN")}`;

  // Analyze ONLY when the user clicks the button
  const analyzeRevenue = async () => {
    try {
      setLoading(true);
      setExecution(null);

      const analysisResponse = await fetch(`${API}/api/analyze`);

      if (!analysisResponse.ok) {
        throw new Error("Analysis failed");
      }

      const analysisData = await analysisResponse.json();
      setAnalysis(analysisData);

      const planResponse = await fetch(`${API}/api/recovery-plan`);

      if (!planResponse.ok) {
        throw new Error("Recovery plan failed");
      }

      const planData = await planResponse.json();
      console.log("RECOVERY PLAN:", planData);

      setRecoveryPlan(planData);
    } catch (error) {
      console.error(error);
      alert(
        "Could not connect to the backend. Make sure the backend terminal is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // Generate/reload the recovery plan
  const generateRecoveryPlan = async () => {
    try {
      setLoading(true);

      const response = await fetch(`${API}/api/recovery-plan`);

      if (!response.ok) {
        throw new Error("Recovery plan failed");
      }

      const data = await response.json();

      console.log("RECOVERY PLAN:", data);

      setRecoveryPlan(data);
    } catch (error) {
      console.error(error);
      alert("Unable to generate recovery plan.");
    } finally {
      setLoading(false);
    }
  };

  // Approve and execute the recovery plan
  const approveRecoveryPlan = async () => {
    try {
      setExecuting(true);

      const response = await fetch(`${API}/api/execute-recovery`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      console.log("EXECUTION RESULT:", data);

      setExecution(data);
    } catch (error) {
      console.error(error);
      alert("Unable to execute recovery plan.");
    } finally {
      setExecuting(false);
    }
  };

  const plan = recoveryPlan || {};

  const recoveryPercentage =
    analysis?.revenue_at_risk && plan.estimated_recovery
      ? Math.min(
          (Number(plan.estimated_recovery) /
            Number(analysis.revenue_at_risk)) *
            100,
          100
        )
      : 0;

  return (
    <div className="app">

      {/* HEADER */}
      <header className="header">
        <div className="brand">
          <div className="logo">R</div>

          <div>
            <div className="brand-name">
              Revenue Rescue AI
            </div>

            <div className="brand-subtitle">
              AI Revenue Recovery
            </div>
          </div>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          AI ENGINE ONLINE
        </div>
      </header>


      <main>

        {/* HERO */}
        <section className="hero">

          <div className="hero-left">

            <h1>
              Recover revenue
              <br />
              <span>before it's lost.</span>
            </h1>

            <p>
              Revenue Rescue AI analyzes failed payments, predicts recovery
              probability, chooses the safest intervention, and prioritizes
              revenue recovery automatically.
            </p>

            <button onClick={analyzeRevenue}>
              {loading ? "Analyzing..." : "Analyze Revenue →"}
            </button>

          </div>


          <div className="engine-card">

            <div className="eyebrow">
              AI RECOVERY ENGINE
            </div>

            <div className="engine-value">
              {money(plan.estimated_recovery)}
            </div>

            <div className="engine-label">
              estimated recoverable revenue
            </div>

            <div className="progress">
              <div
                style={{
                  width: `${recoveryPercentage}%`,
                }}
              />
            </div>

            <div className="progress-label">
              {recoveryPercentage.toFixed(1)}% of failed value
            </div>

          </div>

        </section>


        {/* METRICS */}
        <section className="metrics">

          <div className="metric-card">
            <div className="eyebrow">
              TRANSACTIONS
            </div>

            <div className="metric-value">
              {analysis
                ? Number(
                    analysis.total_transactions || 0
                  ).toLocaleString("en-IN")
                : "0"}
            </div>

            <div className="metric-label">
              analyzed
            </div>
          </div>


          <div className="metric-card">
            <div className="eyebrow">
              FAILED PAYMENTS
            </div>

            <div className="metric-value">
              {analysis
                ? Number(
                    analysis.failed_transactions || 0
                  ).toLocaleString("en-IN")
                : "0"}
            </div>

            <div className="metric-label">
              {analysis?.failure_rate || 0}% failure rate
            </div>
          </div>


          <div className="metric-card">
            <div className="eyebrow">
              REVENUE AT RISK
            </div>

            <div className="metric-value">
              {money(analysis?.revenue_at_risk)}
            </div>

            <div className="metric-label">
              failed transaction value
            </div>
          </div>


          <div className="metric-card highlight">
            <div className="eyebrow">
              POTENTIALLY RECOVERABLE
            </div>

            <div className="metric-value">
              {money(analysis?.potentially_recoverable)}
            </div>

            <div className="metric-label">
              {analysis?.recoverable_percentage || 0}% opportunity scenario
            </div>
          </div>

        </section>


        {/* AI DETECTION */}
        <section className="section">

          <div className="eyebrow">
            AI DETECTION
          </div>

          <h2>
            Where revenue is at risk
          </h2>

          <div className="detection-card">

            <div>
              <strong>
                UPI failure spike
              </strong>

              <p>
                {analysis?.ai_detection ||
                  "Click Analyze Revenue to detect payment patterns."}
              </p>
            </div>

            <div className="detection-number">
              {analysis?.evening_upi_failure_rate || 0}%

              <span>
                failure rate
              </span>
            </div>

          </div>

        </section>


        {/* RECOVERY STRATEGY */}
        <section className="section">

          <div className="eyebrow">
            RECOVERY STRATEGY
          </div>

          <h2>
            Recovery plan
          </h2>

          <p className="section-description">
            Failed transactions are scored and prioritized according to
            their recovery potential.
          </p>

          <button
            className="outline-button"
            onClick={generateRecoveryPlan}
          >
            {loading
              ? "Generating..."
              : "Generate Recovery Plan →"}
          </button>


          <div className="recovery-grid">

            {/* RETRY */}
            <div className="recovery-card">

              <div className="big-number">
                {plan.retry_count || 0}
              </div>

              <div className="card-title">
                RETRY
              </div>

              <div className="card-description">
                High-priority recovery opportunities
              </div>

              <div className="card-money">
                {money(plan.retry_value)}
              </div>

            </div>


            {/* REMINDER */}
            <div className="recovery-card">

              <div className="big-number">
                {plan.reminder_count || 0}
              </div>

              <div className="card-title">
                SEND REMINDER
              </div>

              <div className="card-description">
                Customer recovery opportunities
              </div>

              <div className="card-money">
                {money(plan.reminder_value)}
              </div>

            </div>


            {/* HUMAN REVIEW */}
            <div className="recovery-card">

              <div className="big-number">
                {plan.human_review_count || 0}
              </div>

              <div className="card-title">
                HUMAN REVIEW
              </div>

              <div className="card-description">
                High-value or sensitive cases
              </div>

              <div className="card-money">
                {money(plan.human_review_value)}
              </div>

            </div>


            {/* ESTIMATED RECOVERY */}
            <div className="recovery-card dark">

              <div className="big-number">
                {money(plan.estimated_recovery)}
              </div>

              <div className="card-title">
                ESTIMATED RECOVERY
              </div>

              <div className="card-description">
                Potential recovered revenue
              </div>

            </div>

          </div>


          {/* PRIORITY QUEUE */}
          <div className="eyebrow queue-label">
            TOP RECOVERY CANDIDATES
          </div>

          <h2>
            Priority queue
          </h2>


          <div className="queue">

            {(plan.recovery_plan || [])
              .slice(0, 5)
              .map((item, index) => (

                <div
                  className="queue-row"
                  key={item.transaction_id || index}
                >

                  <div>
                    <strong>
                      {item.transaction_id}
                    </strong>

                    <span>
                      {item.payment_method} ·{" "}
                      {item.failure_reason}
                    </span>
                  </div>


                  <div className="queue-amount">
                    {money(item.amount)}
                  </div>


                  <div className="queue-score">

                    {Number(
                      item.recovery_score || 0
                    ).toFixed(2)}

                    <span>
                      RECOVERY SCORE
                    </span>

                  </div>


                  <div className="queue-action">
                    {item.recommended_action}
                  </div>

                </div>

              ))}

          </div>


          {/* APPROVAL */}
          {recoveryPlan && (
            <div className="approval-card">

              <div>
                <div className="approval-title">
                  Recovery plan ready
                </div>

                <div className="safety-text">
                  AI recommendations have passed the configured safety
                  rules. High-value and low-confidence transactions are
                  routed to human review.
                </div>
              </div>

              <button
                className="approval-button"
                onClick={approveRecoveryPlan}
                disabled={executing}
              >
                {executing
                  ? "Executing..."
                  : "Approve Recovery Plan →"}
              </button>

            </div>
          )}


          {/* EXECUTION RESULT */}
          {execution && (
            <div className="execution-card">

              <div className="eyebrow">
                EXECUTION RESULT
              </div>

              <h2>
                {execution.status === "ALREADY_EXECUTED"
                  ? "Recovery campaign already executed"
                  : money(execution.recovered_revenue)}
              </h2>

              {execution.status === "ALREADY_EXECUTED" ? (

                <p>
                  Duplicate execution was prevented by the safety and
                  idempotency layer.
                </p>

              ) : (

                <div className="execution-grid">

                  <div>
                    <strong>
                      {execution.retry_actions || 0}
                    </strong>

                    <span>
                      retry actions
                    </span>
                  </div>

                  <div>
                    <strong>
                      {execution.reminders_sent || 0}
                    </strong>

                    <span>
                      payment reminders
                    </span>
                  </div>

                  <div>
                    <strong>
                      {execution.human_reviews || 0}
                    </strong>

                    <span>
                      transactions escalated
                    </span>
                  </div>

                </div>

              )}

              <div className="safety-text">
                simulation mode: no real payments were processed
              </div>

            </div>
          )}

        </section>


        {/* DECISION LOGIC */}
        <section className="section">

          <div className="eyebrow">
            DECISION LOGIC
          </div>

          <h2>
            Detect → Score → Decide → Recover
          </h2>


          <div className="steps">

            <div>
              <span>01</span>
              <strong>Detect</strong>
              <p>
                Identify failed payments and revenue at risk.
              </p>
            </div>

            <div>
              <span>02</span>
              <strong>Score</strong>
              <p>
                Estimate recovery probability for each intervention.
              </p>
            </div>

            <div>
              <span>03</span>
              <strong>Decide</strong>
              <p>
                Select retry, reminder, or human review.
              </p>
            </div>

            <div>
              <span>04</span>
              <strong>Recover</strong>
              <p>
                Execute safely and record every decision.
              </p>
            </div>

          </div>

        </section>

      </main>


      <footer>
        Revenue Rescue AI · AI Revenue Recovery
      </footer>

    </div>
  );
}

export default App;