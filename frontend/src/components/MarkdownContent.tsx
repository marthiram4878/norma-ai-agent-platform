import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = "" }: MarkdownContentProps) {
  if (!content.trim()) {
    return <p className={`text-slate-600 ${className}`}>—</p>;
  }

  return (
    <div className={`markdown-body text-[13px] leading-7 text-slate-300 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-3 mt-6 text-xl font-semibold text-slate-100 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-5 text-lg font-semibold text-slate-100 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-4 text-base font-semibold text-slate-200 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          ul: ({ children }) => (
            <ul className="mb-3 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-3 list-decimal space-y-1 pl-5 last:mb-0">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-6">{children}</li>,
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-cyan-300 underline decoration-cyan-400/40 underline-offset-2 hover:text-cyan-200"
              target="_blank"
              rel="noreferrer"
            >
              {children}
            </a>
          ),
          code: ({ className: codeClass, children }) => {
            const isBlock = Boolean(codeClass);
            if (isBlock) {
              return (
                <code className="block overflow-x-auto rounded-lg border border-white/8 bg-[#0a0f18] p-3 text-[12px] leading-5 text-slate-300">
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-white/8 px-1 py-0.5 text-[12px] text-cyan-100">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="mb-3 overflow-x-auto last:mb-0">{children}</pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mb-3 border-l-2 border-cyan-400/30 pl-3 text-slate-400 last:mb-0">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-4 border-white/10" />,
          table: ({ children }) => (
            <div className="mb-3 overflow-x-auto last:mb-0">
              <table className="w-full border-collapse text-left text-[12px]">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-white/10 bg-white/[0.04] px-2 py-1.5 font-medium text-slate-200">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-white/10 px-2 py-1.5 text-slate-400">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
