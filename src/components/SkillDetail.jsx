import { Check } from 'lucide-react';
import { useState } from 'react';
import { Modal } from './Modal.jsx';
import { PixelSprite } from './PixelArt';

export function SkillDetail({
  skill,
  onClose,
  mode,
}) {
  const [tab, setTab] = useState('Contract');

  const contract = {
    name: skill.id,
    version: skill.version,
    status: skill.draft ? 'draft' : 'validated',

    inputs: skill.id === 'sales_analysis'
      ? {
          csv_path: 'string',
          column_mapping: {
            product: 'Product',
            revenue: 'Sales',
            date: 'OrderDate',
          },
        }
      : {
          source: 'string',
          output_format: 'string',
        },

    allowed_tools: skill.tools,

    validation: skill.draft
      ? 'pending'
      : {
          framework: 'pytest',
          passed: skill.tests,
          total: skill.tests,
        },
  };

  const testNames = skill.id === 'sales_analysis'
    ? [
        'test_column_alias_mapping',
        'test_revenue_aggregation',
        'test_missing_values',
      ]
    : [
        'test_valid_input',
        'test_output_contract',
        'test_missing_values',
        'test_tool_allowlist',
        'test_edge_cases',
        'test_empty_input',
        'test_error_handling',
        'test_consistency',
      ];

  return (
    <Modal
      title={skill.name}
      eyebrow="A CAPABILITY WITH A STORY"
      onClose={onClose}
      className={skill.kind}
    >
      <div className="modal-body">
        <div className="skill-detail-intro">
          <PixelSprite
            kind={skill.kind}
            mode={mode}
          />

          <div>
            <p>{skill.description}</p>

            <span className="version">
              v{skill.version}
            </span>

            <span className="detail-category">
              {skill.category} · {skill.runs} runs
            </span>
          </div>
        </div>

        <div className="detail-tabs">
          {[
            'Contract',
            'Tests',
            'Version history',
          ].map((value) => (
            <button
              key={value}
              className={
                tab === value ? 'selected' : ''
              }
              onClick={() => setTab(value)}
            >
              {value}
            </button>
          ))}
        </div>

        {tab === 'Contract' && (
          <pre className="code-block">
            {JSON.stringify(contract, null, 2)}
          </pre>
        )}

        {tab === 'Tests' && (
          skill.draft ? (
            <div className="empty-state">
              A new idea, waiting for its first test.
              Draft skills are not yet validated.
            </div>
          ) : (
            <>
              <div className="test-list">
                {Array.from(
                  { length: skill.tests },
                  (_, index) => (
                    <div key={index}>
                      <span>{testNames[index]}</span>

                      <span>
                        <Check size={12} />
                        PASSED
                      </span>
                    </div>
                  ),
                )}
              </div>

              <p className="modal-note">
                Illustrative results for this frontend preview.
              </p>
            </>
          )
        )}

        {tab === 'Version history' && (
          <div className="version-history">
            <div>
              <span className="history-node" />

              <span className="version">
                v{skill.version}
              </span>

              <h3>
                {skill.draft
                  ? 'An idea is born.'
                  : 'A little smarter than before.'}
              </h3>

              <p>
                {skill.draft
                  ? 'Created as a local draft. Code generation, tool scoping, and tests come next.'
                  : skill.id === 'sales_analysis'
                    ? 'Mapped revenue → Sales, normalized column aliases, and passed all three checks. Ready to reuse.'
                    : 'Validated the input contract and expected output, then promoted the skill to the registry.'}
              </p>
            </div>

            {!skill.draft && (
              <div>
                <span className="history-node" />
                <span className="version">v1.0</span>

                <h3>Everyone starts somewhere.</h3>

                <p>
                  Created from a task, scoped to approved
                  tools, and sent through evaluation.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
