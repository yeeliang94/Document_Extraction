import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "DocWeaver2 — Enterprise Test",
  description: "Simplified pipeline test for enterprise proxy",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <style>{`
          *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #faf9f7;
            color: #191919;
            line-height: 1.5;
          }
          .container { max-width: 960px; margin: 0 auto; padding: 24px; }
          h1 { font-size: 24px; font-weight: 600; margin-bottom: 16px; }
          h2 { font-size: 18px; font-weight: 600; margin-bottom: 12px; }
          .card {
            background: #fff;
            border: 1px solid #e8e5df;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
          }
          .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid #e8e5df;
            background: #fff;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.15s;
          }
          .btn:hover { border-color: #c78c2e; color: #c78c2e; }
          .btn-primary {
            background: #191919;
            color: #fff;
            border-color: #191919;
          }
          .btn-primary:hover { background: #333; border-color: #333; color: #fff; }
          .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 500;
          }
          .badge-green { background: #e6f4ea; color: #1a7f37; }
          .badge-yellow { background: #fff8e1; color: #9a6700; }
          .badge-red { background: #ffeef0; color: #d1242f; }
          .badge-blue { background: #e8f0fe; color: #1a56db; }
          .badge-gray { background: #f0eeea; color: #666; }
          table { width: 100%; border-collapse: collapse; font-size: 14px; }
          th { text-align: left; padding: 8px 12px; border-bottom: 2px solid #e8e5df; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #666; }
          td { padding: 8px 12px; border-bottom: 1px solid #f0eeea; }
          tr:hover td { background: #faf9f7; }
          .text-right { text-align: right; }
          .text-muted { color: #888; }
          .text-sm { font-size: 13px; }
          a { color: #191919; text-decoration: none; }
          a:hover { color: #c78c2e; }
          .progress-bar {
            height: 8px;
            background: #f0eeea;
            border-radius: 4px;
            overflow: hidden;
          }
          .progress-fill {
            height: 100%;
            background: #c78c2e;
            border-radius: 4px;
            transition: width 0.3s ease;
          }
          .nav {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 24px;
            border-bottom: 1px solid #e8e5df;
            background: #fff;
            margin-bottom: 24px;
          }
          .nav-brand { font-weight: 700; font-size: 16px; }
          .upload-zone {
            border: 2px dashed #e8e5df;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: border-color 0.15s;
          }
          .upload-zone:hover { border-color: #c78c2e; }
          .upload-zone.dragover { border-color: #c78c2e; background: #fff8e1; }
          .field-value { font-variant-numeric: tabular-nums; font-family: "IBM Plex Mono", monospace; }
          .page-thumb {
            border: 1px solid #e8e5df;
            border-radius: 8px;
            overflow: hidden;
            cursor: pointer;
          }
          .page-thumb:hover { border-color: #c78c2e; }
          .page-thumb img { width: 100%; display: block; }
        `}</style>
      </head>
      <body>
        <nav className="nav">
          <a href="/" className="nav-brand">DocWeaver2</a>
          <span className="text-muted text-sm">Enterprise Test</span>
        </nav>
        {children}
      </body>
    </html>
  );
}
