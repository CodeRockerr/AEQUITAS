import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  children: string;
  fontSize?: string;
}

/**
 * Renders LLM-generated markdown (theses, critiques, chat replies) with the
 * site's own typography instead of react-markdown's default styles - the
 * AI output regularly includes **bold**, ### headers, and GFM tables, which
 * were previously dumped as raw text (literal asterisks/pipes) wherever a
 * component rendered `{someLlmText}` directly.
 */
export function Markdown({ children, fontSize = "14px" }: MarkdownProps) {
  return (
    <div
      style={{
        fontFamily: "var(--font-sans)",
        fontSize,
        color: "var(--text-secondary)",
        lineHeight: "1.8",
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "20px",
                color: "var(--text-primary)",
                margin: "20px 0 12px",
              }}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "17px",
                color: "var(--text-primary)",
                margin: "20px 0 10px",
              }}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "var(--text-primary)",
                margin: "20px 0 8px",
              }}
            >
              {children}
            </h3>
          ),
          p: ({ children }) => <p style={{ margin: "0 0 14px" }}>{children}</p>,
          strong: ({ children }) => (
            <strong style={{ color: "var(--text-primary)", fontWeight: 600 }}>
              {children}
            </strong>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: "0 0 14px", paddingLeft: "20px" }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: "0 0 14px", paddingLeft: "20px" }}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ marginBottom: "6px" }}>{children}</li>
          ),
          hr: () => (
            <hr
              style={{
                border: "none",
                borderTop: "1px solid var(--border-subtle)",
                margin: "20px 0",
              }}
            />
          ),
          table: ({ children }) => (
            <div style={{ overflowX: "auto", margin: "0 0 14px" }}>
              <table
                style={{
                  borderCollapse: "collapse",
                  width: "100%",
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                }}
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead
              style={{
                borderBottom: "1px solid var(--border-default)",
              }}
            >
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th
              style={{
                textAlign: "left",
                padding: "6px 12px 6px 0",
                color: "var(--text-tertiary)",
                fontWeight: 500,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                fontSize: "10px",
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                padding: "8px 12px 8px 0",
                borderBottom: "1px solid var(--border-subtle)",
                color: "var(--text-secondary)",
                verticalAlign: "top",
              }}
            >
              {children}
            </td>
          ),
          code: ({ children }) => (
            <code
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.9em",
                background: "var(--bg-elevated)",
                padding: "1px 5px",
                borderRadius: "var(--radius-sm)",
              }}
            >
              {children}
            </code>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
