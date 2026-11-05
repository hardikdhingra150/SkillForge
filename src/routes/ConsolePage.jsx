import { Console } from '../components/Console.jsx';
import { PageHeading } from '../components/ui.jsx';

export function ConsolePage({ consoleProps }) {
  return (
    <>
      <PageHeading
        label="SAMPLE RUN · REAL ENGINE"
        title="See the learning loop."
        description="This runs a real task against your API with a small sample CSV. Nothing here is pre-recorded."
      />

      <Console
        {...consoleProps}
        expanded
      />

      <div className="console-explain">
        <article>
          <span>01 / THE PLOT TWIST</span>

          <h3>
            Your CSV says “$1,200.50”.
            <br />
            The skill expects a plain number.
          </h3>

          <p>
            v1.0.0 fails with BAD_NUMBER. Patch
            diagnoses it, switches to parse_amount,
            and proves the fix on the failing input.
          </p>
        </article>

        <article>
          <span>02 / THE HAPPY ENDING</span>

          <h3>
            Every test passes.
            <br />
            A better skill stays with you.
          </h3>

          <p>
            v1.1.0 joins the registry. Run the
            same task again and the worker
            reuses it with no repair.
          </p>
        </article>
      </div>
    </>
  );
}
