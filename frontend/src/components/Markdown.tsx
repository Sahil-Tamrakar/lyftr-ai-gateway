import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

const components: Components = {
  // Let highlighted blocks supply their own container.
  pre({ children }) {
    return <>{children}</>;
  },
  code({ node, className, children, ...props }) {
    const match = /language-([\w-]+)/.exec(className ?? "");
    const text = String(children ?? "").replace(/\n$/, "");
    const isBlock = Boolean(match) || text.includes("\n");

    if (isBlock) {
      return (
        <SyntaxHighlighter
          language={match?.[1] ?? "text"}
          style={oneDark}
          PreTag="div"
          customStyle={{
            margin: "0.75rem 0",
            padding: "0.9rem 1rem",
            borderRadius: "0.6rem",
            border: "1px solid rgba(148, 163, 184, 0.12)",
            background: "#0b1220",
            fontSize: "12.5px",
            lineHeight: 1.6,
          }}
          codeTagProps={{ style: { fontFamily: "inherit" } }}
        >
          {text}
        </SyntaxHighlighter>
      );
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  a({ node, children, ...props }) {
    return (
      <a {...props} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    );
  },
};

export function Markdown({ content }: { content: string }) {
  return (
    <div className="prose-chat">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
